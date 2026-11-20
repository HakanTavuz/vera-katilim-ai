(() => {
  const secureMode = document.body.dataset.secureMode === "true";
  const toggle = document.getElementById("chat-toggle");
  const panel = document.getElementById("chat-panel");
  const closeBtn = document.getElementById("chat-close");
  const log = document.getElementById("chat-log");
  const form = document.getElementById("chat-form");
  const input = document.getElementById("chat-input");
  if (!toggle || !panel) return;

  const open = () => { panel.hidden = false; input.focus(); };
  const close = () => { panel.hidden = true; };
  toggle.addEventListener("click", () => (panel.hidden ? open() : close()));
  closeBtn.addEventListener("click", close);

  function bubble(kind) {
    const el = document.createElement("div");
    el.className = `chat-msg chat-${kind}`;
    log.appendChild(el);
    log.scrollTop = log.scrollHeight;
    return el;
  }

  function showText(text, kind) {
    bubble(kind).textContent = text;
  }

  function showBotReply(text) {
    const el = bubble("bot");
    // VULN-12: model output written with innerHTML | OWASP: LLM05:2025 Improper Output Handling
    if (secureMode) {
      el.textContent = text;
    } else {
      el.innerHTML = text.replace(/\n/g, "<br>");
    }
    log.scrollTop = log.scrollHeight;
  }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) {
      window.location.href = "/login";
      throw new Error("login");
    }
    return res.json();
  }

  function draftCard(draft) {
    const card = bubble("bot");
    card.classList.add("w-full");

    const title = document.createElement("p");
    title.className = "font-semibold text-navy-900";
    title.textContent = `Transfer taslağı #${draft.id}`;

    const details = document.createElement("p");
    details.className = "mt-1 text-sm";
    details.textContent = `${draft.receiver} · ${draft.iban}\n${draft.amount}` +
      (draft.description ? `\nAçıklama: ${draft.description}` : "");

    const actions = document.createElement("div");
    actions.className = "mt-3 flex gap-2";
    const ok = document.createElement("button");
    ok.className = "btn px-3 py-1.5 text-sm";
    ok.textContent = "Onayla";
    const cancel = document.createElement("button");
    cancel.className = "btn btn-light px-3 py-1.5 text-sm";
    cancel.textContent = "İptal";
    actions.append(ok, cancel);

    const status = document.createElement("p");
    status.className = "mt-2 text-xs text-slate-500";

    card.append(title, details, actions, status);

    const finish = (message) => {
      actions.remove();
      status.textContent = message;
    };
    ok.addEventListener("click", async () => {
      ok.disabled = cancel.disabled = true;
      const r = await post(`/api/assistant/drafts/${draft.id}/confirm`);
      finish(r.message);
    });
    cancel.addEventListener("click", async () => {
      ok.disabled = cancel.disabled = true;
      const r = await post(`/api/assistant/drafts/${draft.id}/cancel`);
      finish(r.message);
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    input.value = "";
    showText(message, "user");

    const typing = bubble("bot");
    typing.textContent = "Yazıyor…";
    try {
      const data = await post("/api/assistant/chat", { message });
      typing.remove();
      showBotReply(data.reply || "");
      (data.drafts || []).forEach(draftCard);
    } catch (err) {
      typing.remove();
      if (err.message !== "login") showText("Bağlantı hatası, lütfen tekrar deneyin.", "error");
    }
  });
})();
