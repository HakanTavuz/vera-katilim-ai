// Cookie preferences page. External file so it runs under the strict CSP in secure mode.
(() => {
  const saveBtn = document.getElementById("cookie-save");
  if (!saveBtn) return;

  const api = window.veraCookies;
  const prefs = (api && api.read()) || { essential: true, analytics: false, marketing: false };
  document.querySelectorAll("[data-pref]").forEach((el) => {
    if (el.dataset.pref !== "essential") el.checked = !!prefs[el.dataset.pref];
  });

  const saved = document.getElementById("cookie-saved");
  saveBtn.addEventListener("click", () => {
    const value = { essential: true };
    document.querySelectorAll("[data-pref]").forEach((el) => { value[el.dataset.pref] = el.checked; });
    if (api) api.save(value);
    const banner = document.getElementById("cookie-banner");
    if (banner) banner.hidden = true;
    if (saved) { saved.hidden = false; setTimeout(() => (saved.hidden = true), 2500); }
  });
})();
