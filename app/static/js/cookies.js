// Cookie consent, stored per browser. Default is essential-only (privacy first).
(() => {
  const KEY = "vera_cookie_consent";
  const banner = document.getElementById("cookie-banner");

  function read() {
    try { return JSON.parse(localStorage.getItem(KEY) || "null"); }
    catch { return null; }
  }
  function save(value) {
    try { localStorage.setItem(KEY, JSON.stringify({ ...value, ts: Date.now() })); }
    catch { /* private mode: keep going without persisting */ }
  }

  // expose for the preferences page
  window.veraCookies = { read, save };

  if (!banner) return;
  if (!read()) banner.hidden = false;

  banner.querySelectorAll("[data-cookie]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const all = btn.dataset.cookie === "accept";
      save({ essential: true, analytics: all, marketing: all });
      banner.hidden = true;
    });
  });
})();
