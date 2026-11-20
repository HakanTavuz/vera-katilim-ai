from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import Forbidden, LoginRequired, current_user
from app.config import settings
from app.db import init_db
from app.routes import accounts, admin, assistant, render, transfers

CSP = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.tailwindcss.com; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "  # tailwind CDN injects a <style> tag at runtime
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="VERA Katılım AI", description="Eğitim amaçlı, bilerek açık bırakılmış katılım bankası demosu",
              lifespan=lifespan)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    # VULN-03: no CSP, so injected scripts run freely | OWASP: A03:2021 Injection
    if settings.SECURE_MODE:
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Vera-Mode"] = "secure" if settings.SECURE_MODE else "vulnerable"
    return response


# added after the header middleware so it runs first and request.session is ready
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                   session_cookie="securebank_session", same_site="lax", max_age=60 * 60 * 8)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(admin.router)
app.include_router(assistant.router)


@app.exception_handler(LoginRequired)
async def login_required_handler(request: Request, exc: LoginRequired):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Giriş yapmanız gerekiyor"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


@app.exception_handler(Forbidden)
async def forbidden_handler(request: Request, exc: Forbidden):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Yetkiniz yok"}, status_code=403)
    return render(request, "error.html", user=current_user(request), status_code=403,
                  title="Erişim engellendi", message="Bu sayfayı görüntüleme yetkiniz yok.")
