const ext = globalThis.browser ?? globalThis.chrome;
const DEFAULT_API_URL = "http://127.0.0.1:8000";
const CAPABILITIES = ["facebook", "tiktok", "threads"];

let processing = false;

ext.runtime.onInstalled.addListener(() => {
  ext.alarms.create("talent-radar-poll", { periodInMinutes: 1 });
  processQueue();
});

ext.runtime.onStartup.addListener(() => {
  ext.alarms.create("talent-radar-poll", { periodInMinutes: 1 });
  processQueue();
});

ext.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "talent-radar-poll") {
    processQueue();
  }
});

ext.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message)
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});

async function handleMessage(message) {
  if (message?.type === "agent:status") {
    const settings = await getSettings();
    return {
      ok: true,
      paired: Boolean(settings.agentToken),
      apiUrl: settings.apiUrl,
      agent: settings.agent ?? null,
      activeJob: settings.activeJob ?? null,
    };
  }
  if (message?.type === "agent:pair") {
    return pair(message.payload);
  }
  if (message?.type === "agent:disconnect") {
    await ext.storage.local.remove(["agentToken", "agent", "activeJob"]);
    return { ok: true };
  }
  if (message?.type === "agent:poll") {
    processQueue();
    return { ok: true };
  }
  if (message?.type === "agent:sync-connections") {
    const settings = await getSettings();
    if (!settings.agentToken) return { ok: true, paired: false };
    const agent = await sendHeartbeat(settings);
    await ext.storage.local.set({ agent });
    return { ok: true, paired: true, agent };
  }
  if (message?.type === "agent:batch") {
    const settings = await getSettings();
    if (!settings.activeJob || settings.activeJob.id !== message.jobId) {
      throw new Error("Job khong con hoat dong.");
    }
    const job = await apiRequest(
      `/browser-agent/jobs/${message.jobId}/items`,
      {
        method: "POST",
        body: { records: message.records },
      },
      settings,
    );
    return { ok: true, job };
  }
  return { ok: false, error: "Thong diep khong duoc ho tro." };
}

async function pair(payload) {
  const apiUrl = normalizeApiUrl(payload.apiUrl || DEFAULT_API_URL);
  const result = await apiRequest(
    "/browser-agent/pair",
    {
      method: "POST",
      body: {
        pairing_code: payload.pairingCode,
        name: payload.name || defaultAgentName(),
        browser: detectBrowser(),
        version: detectBrowserVersion(),
        capabilities: CAPABILITIES,
      },
    },
    { apiUrl },
  );
  await ext.storage.local.set({
    apiUrl,
    agentToken: result.agent_token,
    agent: result.agent,
  });
  ext.alarms.create("talent-radar-poll", { periodInMinutes: 1 });
  processQueue();
  return { ok: true, agent: result.agent };
}

async function processQueue() {
  if (processing) return;
  processing = true;
  let settings;
  try {
    settings = await getSettings();
    if (!settings.agentToken) return;
    const agent = await sendHeartbeat(settings);
    await ext.storage.local.set({ agent });

    let job = settings.activeJob;
    if (!job) {
      job = await apiRequest(
        "/browser-agent/jobs/claim",
        {
          method: "POST",
          body: { supported_platforms: CAPABILITIES },
        },
        settings,
      );
      if (!job) return;
      await ext.storage.local.set({ activeJob: job });
      settings.activeJob = job;
    }
    await executeJob(job, settings);
  } catch (error) {
    const activeJob = settings?.activeJob;
    if (activeJob && settings?.agentToken) {
      await failJob(activeJob, settings, error.message);
    }
    await ext.storage.local.set({ lastError: error.message });
  } finally {
    processing = false;
  }
}

async function sendHeartbeat(settings) {
  return apiRequest(
    "/browser-agent/heartbeat",
    {
      method: "POST",
      body: {
        browser: detectBrowser(),
        version: detectBrowserVersion(),
        capabilities: CAPABILITIES,
        connections: await detectPlatformConnections(),
      },
    },
    settings,
  );
}

async function detectPlatformConnections() {
  const facebook = await firstCookie(
    "https://www.facebook.com/",
    ["c_user"],
  );
  const tiktok = await firstCookie(
    "https://www.tiktok.com/",
    ["sessionid", "sessionid_ss"],
  );
  const threads =
    (await firstCookie("https://www.threads.net/", ["sessionid"])) ??
    (await firstCookie("https://www.instagram.com/", ["sessionid"]));
  return [
    {
      platform: "facebook",
      connected: Boolean(facebook),
      account_id: facebook?.value || null,
    },
    { platform: "tiktok", connected: Boolean(tiktok) },
    { platform: "threads", connected: Boolean(threads) },
  ];
}

async function firstCookie(url, names) {
  for (const name of names) {
    const cookie = await ext.cookies.get({ url, name });
    if (cookie?.value) return cookie;
  }
  return null;
}

async function executeJob(job, settings) {
  let tab;
  try {
    tab = await findOrOpenJobTab(job);
    await waitForTab(tab.id);
    await delay(1800);
    const result = await ext.tabs.sendMessage(tab.id, {
      type: "collector:start",
      job,
    });
    if (!result?.ok) {
      throw new Error(result?.error || "Collector khong tra ve ket qua.");
    }
    await apiRequest(
      `/browser-agent/jobs/${job.id}/complete`,
      {
        method: "POST",
        body: {
          status: "completed",
          posts_collected: result.counts.posts,
          comments_collected: result.counts.comments,
          replies_collected: result.counts.replies,
          metadata: {
            browser: detectBrowser(),
            page_url: result.pageUrl,
          },
        },
      },
      settings,
    );
    await ext.storage.local.remove(["activeJob", "lastError"]);
  } catch (error) {
    await failJob(job, settings, error.message);
  } finally {
    if (tab?.id) {
      await ext.tabs.remove(tab.id).catch(() => undefined);
    }
  }
}

async function failJob(job, settings, error) {
  try {
    await apiRequest(
      `/browser-agent/jobs/${job.id}/complete`,
      {
        method: "POST",
        body: { status: "failed", error: String(error).slice(0, 4000) },
      },
      settings,
    );
    await ext.storage.local.remove("activeJob");
  } catch {
    // Keep the job locally so it can be reported after the API is available again.
  }
}

async function findOrOpenJobTab(job) {
  return ext.tabs.create({ url: job.source_url, active: false });
}

async function waitForTab(tabId) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    const tab = await ext.tabs.get(tabId);
    if (tab.status === "complete") return;
    await delay(500);
  }
  throw new Error("Trang nguon tai qua lau.");
}

async function getSettings() {
  const stored = await ext.storage.local.get([
    "apiUrl",
    "agentToken",
    "agent",
    "activeJob",
  ]);
  return {
    apiUrl: normalizeApiUrl(stored.apiUrl || DEFAULT_API_URL),
    agentToken: stored.agentToken,
    agent: stored.agent,
    activeJob: stored.activeJob,
  };
}

async function apiRequest(path, options, settings) {
  const headers = { "Content-Type": "application/json" };
  if (settings.agentToken) {
    headers["X-Agent-Token"] = settings.agentToken;
  }
  const response = await fetch(`${settings.apiUrl}${path}`, {
    method: options.method,
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API loi ${response.status}.`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function normalizeApiUrl(value) {
  return String(value).trim().replace(/\/+$/, "");
}

function detectBrowser() {
  const userAgent = navigator.userAgent;
  if (/coc_coc_browser/i.test(userAgent)) return "coccoc";
  if (/firefox/i.test(userAgent)) return "firefox";
  if (/edg/i.test(userAgent)) return "edge";
  if (/opr/i.test(userAgent)) return "opera";
  return "chrome";
}

function detectBrowserVersion() {
  const match = navigator.userAgent.match(
    /(?:coc_coc_browser|firefox|edg|opr|chrome)\/([\d.]+)/i,
  );
  return match?.[1] ?? null;
}

function defaultAgentName() {
  const labels = {
    coccoc: "Coc Coc",
    firefox: "Firefox",
    edge: "Microsoft Edge",
    opera: "Opera",
    chrome: "Google Chrome",
  };
  return `${labels[detectBrowser()]} - ${navigator.platform}`;
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}
