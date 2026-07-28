const ext = globalThis.browser ?? globalThis.chrome;
const pairForm = document.querySelector("#pair-form");
const agentPanel = document.querySelector("#agent-panel");
const connectionLabel = document.querySelector("#connection-label");
const statusDot = document.querySelector("#status-dot");
const agentNameLabel = document.querySelector("#agent-name-label");
const jobLabel = document.querySelector("#job-label");
const message = document.querySelector("#message");
const pollButton = document.querySelector("#poll-button");
const disconnectButton = document.querySelector("#disconnect-button");

document.querySelector("#agent-name").value = `Trình duyệt ${navigator.platform}`;

pairForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setBusy(true);
  showMessage("Đang ghép nối...");
  const form = new FormData(pairForm);
  const response = await send({
    type: "agent:pair",
    payload: {
      pairingCode: form.get("pairingCode"),
      name: form.get("agentName"),
      apiUrl: form.get("apiUrl"),
    },
  });
  setBusy(false);
  if (!response?.ok) {
    showMessage(response?.error || "Không thể ghép nối.", true);
    return;
  }
  showMessage("Đã ghép nối với website trung tâm.");
  await render();
});

pollButton.addEventListener("click", async () => {
  pollButton.disabled = true;
  showMessage("Đang kiểm tra hàng đợi...");
  await send({ type: "agent:poll" });
  window.setTimeout(async () => {
    pollButton.disabled = false;
    await render();
  }, 800);
});

disconnectButton.addEventListener("click", async () => {
  await send({ type: "agent:disconnect" });
  showMessage("Đã ngắt extension trên trình duyệt này.");
  await render();
});

for (const button of document.querySelectorAll("[data-platform-url]")) {
  button.addEventListener("click", () => {
    ext.tabs.create({ url: button.dataset.platformUrl, active: true });
  });
}

async function render() {
  const response = await send({ type: "agent:status" });
  const paired = Boolean(response?.paired);
  pairForm.hidden = paired;
  agentPanel.hidden = !paired;
  statusDot.classList.toggle("online", paired);
  connectionLabel.textContent = paired ? "Đã ghép nối" : "Chưa ghép nối";
  if (paired) {
    agentNameLabel.textContent = response.agent?.name || "Browser Agent";
    jobLabel.textContent = response.activeJob ? "Đang thu thập" : "Sẵn sàng";
    document.querySelector("#api-url").value = response.apiUrl;
  }
}

function setBusy(value) {
  for (const element of pairForm.elements) element.disabled = value;
}

function showMessage(value, isError = false) {
  message.textContent = value;
  message.classList.toggle("error", isError);
}

async function send(messagePayload) {
  try {
    return await ext.runtime.sendMessage(messagePayload);
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

render();
