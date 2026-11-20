// Interactive VeraCard preview — vanilla, no dependencies. Live-mirrors the form
// onto a flipping card. It is a visual demo and stores or sends nothing.
(() => {
  const root = document.querySelector("[data-cardform]");
  if (!root) return;

  const card = root.querySelector("[data-cf-card]");
  const numberEl = root.querySelector("[data-cf-number]");
  const nameEl = root.querySelector("[data-cf-name]");
  const expEl = root.querySelector("[data-cf-exp]");
  const cvvEl = root.querySelector("[data-cf-cvv]");
  const msg = root.querySelector("[data-cf-msg]");
  const inputs = {};
  root.querySelectorAll("[data-cf-in]").forEach((el) => (inputs[el.dataset.cfIn] = el));

  // fill year options (current year .. +10)
  const yearSel = inputs.year;
  if (yearSel) {
    const y0 = new Date().getFullYear();
    for (let y = y0; y <= y0 + 10; y++) {
      const o = document.createElement("option");
      o.value = String(y); o.textContent = String(y);
      yearSel.appendChild(o);
    }
  }

  function renderNumber() {
    const digits = (inputs.number.value || "").replace(/\D/g, "").slice(0, 16);
    // keep the input formatted in groups of four
    inputs.number.value = digits.replace(/(.{4})/g, "$1 ").trim();
    let html = "";
    for (let i = 0; i < 16; i++) {
      if (i > 0 && i % 4 === 0) html += '<b class="is-dim"> </b>';
      const d = digits[i];
      html += `<b class="${d ? "" : "is-dim"}">${d || "#"}</b>`;
    }
    numberEl.innerHTML = html;
  }

  function renderName() {
    const v = (inputs.name.value || "").trim();
    nameEl.textContent = v ? v.toUpperCase() : "AD SOYAD";
  }

  function renderExp() {
    const m = inputs.month.value, y = inputs.year.value;
    expEl.textContent = (m || "AA") + "/" + (y ? y.slice(2) : "YY");
  }

  function renderCvv() {
    const n = (inputs.cvv.value || "").replace(/\D/g, "").slice(0, 4);
    inputs.cvv.value = n;
    cvvEl.textContent = "•".repeat(n.length) || "•••";
  }

  inputs.number.addEventListener("input", renderNumber);
  inputs.name.addEventListener("input", renderName);
  inputs.month.addEventListener("change", renderExp);
  inputs.year.addEventListener("change", renderExp);
  inputs.cvv.addEventListener("input", renderCvv);
  inputs.cvv.addEventListener("focus", () => card.classList.add("is-flipped"));
  inputs.cvv.addEventListener("blur", () => card.classList.remove("is-flipped"));

  root.querySelector("[data-cf-formel]").addEventListener("submit", (e) => {
    e.preventDefault();
    if (msg) { msg.hidden = false; }
  });

  renderNumber(); renderName(); renderExp(); renderCvv();
})();
