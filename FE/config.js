// Auto-select API base by environment; set window.IPOOR_API_BASE to override.
(() => {
  if (window.IPOOR_API_BASE) return;
  const storageKey = "ipoor_api_base";
  const saved =
    sessionStorage.getItem(storageKey) || localStorage.getItem(storageKey);
  if (saved) {
    window.IPOOR_API_BASE = saved;
    return;
  }
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    window.IPOOR_API_BASE = "http://127.0.0.1:8000";
    return;
  }
  window.IPOOR_API_BASE = `${window.location.origin}/api`;
})();
