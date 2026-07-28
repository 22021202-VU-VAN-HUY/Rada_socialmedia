const talentRadarExtension = globalThis.browser ?? globalThis.chrome;

function syncConnections() {
  talentRadarExtension.runtime
    .sendMessage({ type: "agent:sync-connections" })
    .catch(() => undefined);
}

syncConnections();
window.addEventListener("talent-radar:check-connections", syncConnections);
