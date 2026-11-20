from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.config import settings

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def format_money(kurus: int) -> str:
    sign = "-" if kurus < 0 else ""
    lira, kr = divmod(abs(kurus), 100)
    return f"{sign}{lira:,}".replace(",", ".") + f",{kr:02d} TL"


def parse_amount(raw: str) -> int | None:
    """'1.250,50' or '1250.50' -> 125050 kuruş. Returns None if unparseable."""
    raw = (raw or "").strip().replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        value = Decimal(raw)
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    return int((value * 100).to_integral_value())


templates.env.filters["money"] = format_money


def render(request: Request, name: str, user=None, status_code: int = 200, **context):
    context.update(user=user, secure_mode=settings.SECURE_MODE)
    return templates.TemplateResponse(request, name, context, status_code=status_code)
