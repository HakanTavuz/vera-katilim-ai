// Public header: mega-menu panels and the "Online İşlemler" login dropdown.
(() => {
  const triggers = document.querySelectorAll("[data-panel]");
  const panels = {};
  document.querySelectorAll("[data-panel-id]").forEach((p) => (panels[p.dataset.panelId] = p));
  let open = null;

  function close() {
    if (!open) return;
    panels[open].hidden = true;
    const t = document.querySelector(`[data-panel="${open}"]`);
    if (t) t.setAttribute("aria-expanded", "false");
    open = null;
  }
  function show(id) {
    if (open === id) { close(); return; }
    close();
    const panel = panels[id];
    if (!panel) return;
    panel.hidden = false;
    const t = document.querySelector(`[data-panel="${id}"]`);
    if (t) t.setAttribute("aria-expanded", "true");
    open = id;
    const first = panel.querySelector("input, a, button");
    if (first && panel.dataset.panelId === "giris") first.focus();
  }

  triggers.forEach((t) => {
    t.addEventListener("click", (e) => { e.stopPropagation(); show(t.dataset.panel); });
  });
  document.addEventListener("click", (e) => {
    if (open && !e.target.closest("[data-panel-id]") && !e.target.closest("[data-panel]")) close();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
})();
