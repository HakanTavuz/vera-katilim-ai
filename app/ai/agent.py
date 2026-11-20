import re
import threading
from dataclasses import dataclass, field

from app.ai.prompts import SECURE_SYSTEM_PROMPT, VULNERABLE_SYSTEM_PROMPT
from app.ai.tools import ToolContext, run_tool, tool_schemas
from app.auth import RateLimiter
from app.config import settings

MAX_TOOL_ROUNDS = 5
MAX_HISTORY = 10
MAX_MESSAGE_CHARS = 1000

assistant_limiter = RateLimiter(limit=10, window_seconds=60)

_histories: dict[int, list[dict]] = {}
_history_lock = threading.Lock()

INJECTION_PATTERNS = [
    r"(önceki|yukarıdaki|tüm)\s+(talimat|kural|komut)\w*\s+(unut|yok say|görmezden gel|iptal)",
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules)",
    r"system\s*prompt",
    r"sistem\s+(mesaj|talimat|prompt)\w*",
    r"(geliştirici|developer|admin|yönetici)\s+mod",
    r"\bDAN\b|jailbreak",
    r"talimatlar\w*\s+(göster|yaz|söyle|paylaş|tekrarla)",
]

IBAN_RE = re.compile(r"\bTR\d{2}(?:\s?\d){22}\b", re.IGNORECASE)
TC_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?90\s?)?0?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}(?!\d)")


@dataclass
class AgentReply:
    reply: str
    drafts: list = field(default_factory=list)
    tool_calls: list = field(default_factory=list)


def get_history(user_id: int) -> list[dict]:
    with _history_lock:
        return list(_histories.get(user_id, []))


def save_turn(user_id: int, user_msg: str, bot_msg: str) -> None:
    with _history_lock:
        h = _histories.setdefault(user_id, [])
        h += [{"role": "user", "content": user_msg}, {"role": "assistant", "content": bot_msg}]
        del h[:-MAX_HISTORY]


def clear_history(user_id: int) -> None:
    with _history_lock:
        _histories.pop(user_id, None)


def looks_like_injection(text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in INJECTION_PATTERNS)


def mask_sensitive(text: str) -> str:
    text = IBAN_RE.sub(lambda m: "TR** **** **** **** **** " + re.sub(r"\s", "", m.group())[-4:], text)
    text = TC_RE.sub(lambda m: m.group()[:2] + "*******" + m.group()[-2:], text)
    text = PHONE_RE.sub("*** *** ** **", text)
    return text


def build_messages(user, account_id: int, message: str, history: list[dict]) -> list[dict]:
    # VULN-07: user text glued into the same string as the system prompt | OWASP: LLM01:2025 Prompt Injection
    if settings.SECURE_MODE:
        return [{"role": "system", "content": SECURE_SYSTEM_PROMPT}, *history,
                {"role": "user", "content": message}]
    else:
        prompt = VULNERABLE_SYSTEM_PROMPT.format(
            full_name=user["full_name"], customer_id=user["id"], account_id=account_id)
        for turn in history:
            who = "Müşteri" if turn["role"] == "user" else "Asistan"
            prompt += f"\n{who}: {turn['content']}"
        prompt += f"\nMüşteri: {message}\nAsistan:"
        return [{"role": "user", "content": prompt}]


def _client():
    from openai import OpenAI
    return OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL, timeout=60)


def chat(user, account_id: int, message: str, client=None) -> AgentReply:
    message = (message or "").strip()
    if not message:
        return AgentReply("Bir mesaj yazmanız gerekiyor.")

    if settings.SECURE_MODE:
        if not assistant_limiter.allow(str(user["id"])):
            return AgentReply("Çok hızlı mesaj gönderiyorsunuz. Lütfen bir dakika bekleyin.")
        if len(message) > MAX_MESSAGE_CHARS:
            return AgentReply(f"Mesaj en fazla {MAX_MESSAGE_CHARS} karakter olabilir.")
        if looks_like_injection(message):
            return AgentReply("Bu isteği işleyemiyorum. Hesabınızla ilgili başka bir konuda yardımcı olabilirim.")

    if client is None:
        if not settings.DEEPSEEK_API_KEY:
            return AgentReply("API anahtarı tanımlı değil. .env dosyasına DEEPSEEK_API_KEY ekleyin.")
        client = _client()

    ctx = ToolContext(user_id=user["id"], account_id=account_id)
    messages = build_messages(user, account_id, message, get_history(user["id"]))
    log = []

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            resp = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL, messages=messages, tools=tool_schemas(), temperature=0.3,
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                reply = msg.content or ""
                break
            messages.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                               for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                result = run_tool(ctx, tc.function.name, tc.function.arguments)
                log.append({"tool": tc.function.name, "arguments": tc.function.arguments})
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            reply = "İsteğinizi tamamlayamadım, lütfen daha basit bir şekilde tekrar deneyin."
    except Exception as exc:  # network, auth, quota... keep the UI alive
        return AgentReply(f"Asistana şu an ulaşılamıyor ({type(exc).__name__}).", ctx.drafts, log)

    if settings.SECURE_MODE:
        reply = mask_sensitive(reply)

    save_turn(user["id"], message, reply)
    return AgentReply(reply, ctx.drafts, log)
