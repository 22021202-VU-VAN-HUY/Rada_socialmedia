const extensionApi = globalThis.browser ?? globalThis.chrome;

extensionApi.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "collector:start") return false;
  runCollection(message.job)
    .then(sendResponse)
    .catch((error) => sendResponse({ ok: false, error: error.message }));
  return true;
});

async function runCollection(job) {
  const collector = globalThis.TalentRadarCollector?.adapters?.[job.platform];
  if (!collector) {
    throw new Error(`Khong co collector cho ${job.platform}.`);
  }
  const counts = { posts: 0, comments: 0, replies: 0 };
  await collector.collect(job, async (records) => {
    if (records.length === 0) return;
    const response = await extensionApi.runtime.sendMessage({
      type: "agent:batch",
      jobId: job.id,
      records,
    });
    if (!response?.ok) {
      throw new Error(response?.error || "Khong gui duoc du lieu ve Talent Radar.");
    }
    for (const record of records) {
      if (record.item_type === "post") counts.posts += 1;
      if (record.item_type === "comment") counts.comments += 1;
      if (record.item_type === "reply") counts.replies += 1;
    }
  });
  return { ok: true, counts, pageUrl: location.href };
}
