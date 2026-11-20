// Homepage: generic carousels, financing calculator, application tabs, market ticker.
(() => {
  // ---- generic carousel ----
  function initCarousel(root) {
    const track = root.querySelector(".car-track");
    const slides = root.querySelectorAll(".car-slide");
    if (!track || slides.length === 0) return;

    const dotsWrap = root.querySelector("[data-car-dots]");
    const dark = dotsWrap && dotsWrap.hasAttribute("data-dot-dark");
    const prev = root.querySelector("[data-car-prev]");
    const next = root.querySelector("[data-car-next]");
    const toggle = root.querySelector("[data-car-toggle]");
    const icon = root.querySelector("[data-car-icon]");
    const autoplay = parseInt(root.dataset.autoplay || "0", 10);
    let i = 0, playing = autoplay > 0, timer = null;
    let dots = [];

    if (dotsWrap) {
      slides.forEach((_, k) => {
        const b = document.createElement("button");
        b.className = "hero-dot" + (dark ? " is-dark" : "") + (k === 0 ? " is-active" : "");
        b.setAttribute("aria-label", "Slayt " + (k + 1));
        b.addEventListener("click", () => { go(k); restart(); });
        dotsWrap.appendChild(b);
      });
      dots = Array.from(dotsWrap.children);
    }

    function go(n) {
      i = (n + slides.length) % slides.length;
      track.style.transform = `translateX(-${i * 100}%)`;
      dots.forEach((d, k) => d.classList.toggle("is-active", k === i));
    }
    function nx() { go(i + 1); }
    function run() { timer = setInterval(nx, autoplay); }
    function start() { if (autoplay > 0) run(); playing = true; if (icon) icon.textContent = "⏸"; }
    function stop() { clearInterval(timer); playing = false; if (icon) icon.textContent = "▶"; }
    function restart() { if (playing && autoplay > 0) { clearInterval(timer); run(); } }

    if (prev) prev.addEventListener("click", () => { go(i - 1); restart(); });
    if (next) next.addEventListener("click", () => { go(i + 1); restart(); });
    if (toggle) toggle.addEventListener("click", () => (playing ? stop() : start()));
    if (autoplay > 0) start();
  }
  document.querySelectorAll("[data-carousel]").forEach(initCarousel);

  // ---- financing calculator (profit-share, not interest) ----
  const amountEl = document.getElementById("calc-amount");
  if (amountEl) {
    const termEl = document.getElementById("calc-term");
    const out = {
      installment: document.getElementById("calc-installment"),
      rate: document.getElementById("calc-rate"),
      total: document.getElementById("calc-total"),
    };
    const RATE = { 3: 2.59, 6: 2.69, 12: 2.84, 24: 2.99, 36: 3.09 };
    const MIN = 1000, MAX = 2000000;
    const tl = (n) => Math.round(n).toLocaleString("tr-TR") + " TL";
    const digits = (s) => (s.replace(/\D/g, "") || "0");

    function calc() {
      const amount = Math.min(MAX, Math.max(0, parseInt(digits(amountEl.value), 10) || 0));
      const term = parseInt(termEl.value, 10);
      const r = (RATE[term] || 2.84) / 100;
      out.rate.textContent = "%" + RATE[term].toLocaleString("tr-TR", { minimumFractionDigits: 2 });
      if (amount < MIN) { out.installment.textContent = "—"; out.total.textContent = "—"; return; }
      const installment = amount * r / (1 - Math.pow(1 + r, -term));
      out.installment.textContent = tl(installment);
      out.total.textContent = tl(installment * term);
    }
    function format() {
      const v = parseInt(digits(amountEl.value), 10) || 0;
      amountEl.value = v ? v.toLocaleString("tr-TR") : "";
    }
    amountEl.addEventListener("input", () => { format(); calc(); });
    amountEl.addEventListener("blur", () => {
      const v = Math.min(MAX, Math.max(MIN, parseInt(digits(amountEl.value), 10) || MIN));
      amountEl.value = v.toLocaleString("tr-TR");
      calc();
    });
    termEl.addEventListener("change", calc);
    calc();
  }

  // ---- application tabs ----
  const tabs = document.querySelectorAll(".seg-tab");
  if (tabs.length) {
    const panels = document.querySelectorAll("[data-seg-panel]");
    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.classList.toggle("is-active", t === tab));
        panels.forEach((p) => p.classList.toggle("hidden", p.dataset.segPanel !== tab.dataset.seg));
      });
    });
  }

  // ---- currency converter ----
  const conv = document.getElementById("converter");
  if (conv) {
    let rates = {};
    try { rates = JSON.parse(conv.dataset.rates); } catch { rates = { TRY: 1 }; }
    const amountEl = document.getElementById("conv-amount");
    const fromEl = document.getElementById("conv-from");
    const toEl = document.getElementById("conv-to");
    const resultEl = document.getElementById("conv-result");
    const rateEl = document.getElementById("conv-rate");
    const label = (c) => (c === "XAU" ? "Gram Altın" : c);
    const money = (n, c) => n.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: c === "TRY" ? 2 : 4 });

    function convert() {
      const amount = parseFloat((amountEl.value || "0").replace(/\./g, "").replace(",", ".")) || 0;
      const from = fromEl.value, to = toEl.value;
      const out = amount * (rates[from] || 1) / (rates[to] || 1);
      resultEl.textContent = money(out, to) + (to === "XAU" ? " gr" : " " + to);
      const unit = 1 * (rates[from] || 1) / (rates[to] || 1);
      rateEl.textContent = `1 ${label(from)} = ${money(unit, to)} ${to === "XAU" ? "gr" : to}`;
    }
    amountEl.addEventListener("input", convert);
    fromEl.addEventListener("change", convert);
    toEl.addEventListener("change", convert);
    document.getElementById("conv-swap").addEventListener("click", () => {
      const a = fromEl.value; fromEl.value = toEl.value; toEl.value = a; convert();
    });
    convert();
  }

  // ---- market ticker (illustrative values with a small live drift) ----
  const market = document.getElementById("market");
  if (market) {
    let rows = [];
    try { rows = JSON.parse(market.dataset.rows); } catch { rows = []; }
    const num = (n, dec) => n.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: dec });
    const updatedEl = document.getElementById("market-updated");

    function render() {
      market.innerHTML = rows.map((r) => {
        const up = r.d >= 0;
        const dec = r.k.includes("/") ? 4 : 2;  // FX pairs 4 decimals, index/gold 2
        return `<div>
          <p class="text-xs font-semibold uppercase tracking-wide text-navy-500">${r.k}</p>
          <p class="mt-1 font-serif text-xl font-semibold text-navy-900">${num(r.v, dec)}</p>
          <p class="mt-0.5 text-sm font-medium ${up ? "text-emerald-600" : "text-rose-600"}">${up ? "▲" : "▼"} ${num(Math.abs(r.d), 2)}</p>
        </div>`;
      }).join("");
      if (updatedEl) updatedEl.textContent = new Date().toLocaleString("tr-TR");
    }
    function tick() {
      rows.forEach((r) => {
        r.v = Math.max(0, r.v + (Math.random() - 0.5) * r.v * 0.001);
        r.d = +(r.d + (Math.random() - 0.5) * 0.06).toFixed(2);
      });
      render();
    }
    render();
    setInterval(tick, 5000);
  }
})();
