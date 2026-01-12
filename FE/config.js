// Auto-select API base by environment; set window.IPOOR_API_BASE to override.
(() => {
  if (window.IPOOR_API_BASE) return;
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    window.IPOOR_API_BASE = "http://127.0.0.1:8000";
    return;
  }
  window.IPOOR_API_BASE = "https://ipoor.hanzomaster.dev/api";
})();
