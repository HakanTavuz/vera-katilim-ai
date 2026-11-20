import re
import secrets

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from markupsafe import Markup

from app.auth import authenticate, current_user, hash_password, require_customer, require_user
from app.config import settings
from app.crypto import (decrypt_field, encrypt_field, format_iban, iban_index,
                        mask_iban, mask_phone, mask_tc)
from app.db import get_conn
from app.routes import render
from app.routes.transfers import get_primary_account

router = APIRouter()

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{3,32}$")


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def show_description(text: str):
    # VULN-03: transfer description rendered as raw HTML | OWASP: A03:2021 Injection
    if settings.SECURE_MODE:
        return text  # Jinja autoescape handles it, CSP header is the second layer
    else:
        return Markup(text)


def prepare_transactions(rows):
    return [dict(r, description=show_description(r["description"])) for r in rows]


def new_iban() -> str:
    # TR00 0000 prefix keeps these out of the real IBAN space
    return "TR000000" + "".join(secrets.choice("0123456789") for _ in range(18))


# ---------- auth pages ----------

@router.get("/login")
def login_form(request: Request):
    user = current_user(request)
    if user:
        return RedirectResponse("/admin" if user["role"] == "admin" else "/hesabim", status_code=303)
    return render(request, "login.html")


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    user, error = authenticate(username, password, client_ip(request))
    if user is None:
        return render(request, "login.html", error=error, username=username, status_code=401)
    request.session.clear()
    request.session["user_id"] = user["id"]
    return RedirectResponse("/admin" if user["role"] == "admin" else "/hesabim", status_code=303)


@router.get("/register")
def register_form(request: Request):
    return render(request, "register.html", form={})


@router.post("/register")
def register_submit(request: Request, username: str = Form(...), password: str = Form(...),
                    full_name: str = Form(...), phone: str = Form(""), tc_kimlik_no: str = Form(""),
                    address: str = Form("")):
    form = {"username": username, "full_name": full_name, "phone": phone,
            "tc_kimlik_no": tc_kimlik_no, "address": address}

    errors = []
    if not USERNAME_RE.match(username):
        errors.append("Kullanıcı adı 3-32 karakter olmalı, sadece harf, rakam, nokta ve alt çizgi içerebilir.")
    if tc_kimlik_no and not re.fullmatch(r"\d{11}", tc_kimlik_no):
        errors.append("TC kimlik no 11 haneli olmalı.")
    if settings.SECURE_MODE and not (8 <= len(password) <= 64):
        errors.append("Parola 8-64 karakter arası olmalı.")
    if not password:
        errors.append("Parola boş olamaz.")
    if errors:
        return render(request, "register.html", form=form, error=" ".join(errors), status_code=400)

    with get_conn() as conn:
        if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            return render(request, "register.html", form=form, error="Bu kullanıcı adı alınmış.",
                          status_code=400)
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role, tc_kimlik_enc, phone_enc, address) "
            "VALUES (?, ?, ?, 'customer', ?, ?, ?)",
            (username, hash_password(password), full_name.strip()[:80],
             encrypt_field(tc_kimlik_no) if tc_kimlik_no else None,
             encrypt_field(phone) if phone else None, address[:200]),
        )
        iban = new_iban()
        conn.execute(
            "INSERT INTO accounts (user_id, iban_enc, iban_index, iban_last4, balance) VALUES (?, ?, ?, ?, ?)",
            (cur.lastrowid, encrypt_field(iban), iban_index(iban), iban[-4:], 1_000 * 100),
        )
        user_id = cur.lastrowid

    request.session.clear()
    request.session["user_id"] = user_id
    request.session["flash"] = "Hesabınız açıldı. Hoş geldin bonusu olarak 1.000,00 TL tanımlandı."
    return RedirectResponse("/hesabim", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


# ---------- public pages ----------

@router.get("/")
def home(request: Request):
    user = current_user(request)
    # once signed in, the public landing page is out of reach until logout
    if user:
        return RedirectResponse("/admin" if user["role"] == "admin" else "/hesabim", status_code=303)
    return render(request, "home.html", user=None)


@router.get("/urunler")
def products(request: Request):
    return render(request, "products.html", user=current_user(request))


@router.get("/kurumsal")
def corporate(request: Request):
    return render(request, "corporate.html", user=current_user(request))


@router.get("/sube-atm")
def branches(request: Request):
    return render(request, "branches.html", user=current_user(request))


@router.get("/sss")
def faq(request: Request):
    return render(request, "faq.html", user=current_user(request))


@router.get("/cerezler")
def cookies(request: Request):
    user = current_user(request)
    layout = "base.html" if user and user["role"] == "customer" else "public_base.html"
    return render(request, "cookies.html", user=user, layout=layout)


# ---------- customer pages ----------

@router.get("/odemeler")
def payments(request: Request, user=Depends(require_customer)):
    with get_conn() as conn:
        account = get_primary_account(conn, user["id"])
    return render(request, "payments.html", user=user, account=account)


@router.get("/basvurularim")
def my_applications(request: Request, user=Depends(require_customer)):
    with get_conn() as conn:
        drafts = conn.execute(
            "SELECT id, to_iban_last4, amount, description, status, created_at "
            "FROM transfer_drafts WHERE user_id = ? ORDER BY id DESC LIMIT 20",
            (user["id"],),
        ).fetchall()
    return render(request, "applications.html", user=user, drafts=drafts)

@router.get("/kartlar")
def cards(request: Request, user=Depends(require_customer)):
    with get_conn() as conn:
        account = get_primary_account(conn, user["id"])
    # card number is derived from the account id, it is not a stored PAN
    card_no = f"5312 00{account['id']:02d}0 0000 {account['iban_last4']}"
    return render(request, "cards.html", user=user, account=account, card_no=card_no,
                  masked_iban=mask_iban(account["iban_last4"]))


@router.get("/hesabim")
def dashboard(request: Request, user=Depends(require_user)):
    if user["role"] == "admin":
        return RedirectResponse("/admin", status_code=303)
    with get_conn() as conn:
        account = get_primary_account(conn, user["id"])
        rows = conn.execute(
            "SELECT * FROM transactions WHERE account_id = ? ORDER BY created_at DESC, id DESC LIMIT 10",
            (account["id"],),
        ).fetchall()
    return render(request, "dashboard.html", user=user, account=account,
                  masked_iban=mask_iban(account["iban_last4"]),
                  transactions=prepare_transactions(rows),
                  flash=request.session.pop("flash", None))


def _load_account_for(conn, account_id: int, user):
    account = conn.execute(
        "SELECT a.*, u.full_name FROM accounts a JOIN users u ON u.id = a.user_id WHERE a.id = ?",
        (account_id,),
    ).fetchone()
    if account is None:
        return None
    # VULN-02: account is fetched by id without checking who owns it | OWASP: A01:2021 Broken Access Control
    if settings.SECURE_MODE:
        if account["user_id"] != user["id"]:
            return None  # same answer as "not found" so ids can't be enumerated
    return account


@router.get("/account/{account_id}")
def account_detail(request: Request, account_id: int, user=Depends(require_user)):
    with get_conn() as conn:
        account = _load_account_for(conn, account_id, user)
        if account is None:
            return render(request, "error.html", user=user, status_code=404,
                          title="Hesap bulunamadı", message="Bu hesap mevcut değil.")
        rows = conn.execute(
            "SELECT * FROM transactions WHERE account_id = ? ORDER BY created_at DESC, id DESC",
            (account_id,),
        ).fetchall()
    return render(request, "account.html", user=user, account=account,
                  iban=format_iban(decrypt_field(account["iban_enc"])) if not settings.SECURE_MODE
                  else mask_iban(account["iban_last4"]),
                  transactions=prepare_transactions(rows))


@router.get("/api/transactions")
def api_transactions(request: Request, account_id: int, user=Depends(require_user)):
    with get_conn() as conn:
        account = _load_account_for(conn, account_id, user)
        if account is None:
            return JSONResponse({"detail": "Hesap bulunamadı"}, status_code=404)
        rows = conn.execute(
            "SELECT id, counterparty_name, counterparty_last4, amount, description, created_at "
            "FROM transactions WHERE account_id = ? ORDER BY created_at DESC, id DESC",
            (account_id,),
        ).fetchall()
    return {
        "account_id": account_id,
        "owner": account["full_name"],
        "balance": account["balance"] / 100,
        "transactions": [dict(r, amount=r["amount"] / 100) for r in rows],
    }


@router.get("/transactions")
def history(request: Request, q: str = "", direction: str = "all", user=Depends(require_customer)):
    sql = "SELECT * FROM transactions WHERE account_id = ?"
    with get_conn() as conn:
        account = get_primary_account(conn, user["id"])
        params: list = [account["id"]]
        if q:
            sql += " AND (description LIKE ? OR counterparty_name LIKE ?)"
            params += [f"%{q}%", f"%{q}%"]
        if direction == "in":
            sql += " AND amount > 0"
        elif direction == "out":
            sql += " AND amount < 0"
        rows = conn.execute(sql + " ORDER BY created_at DESC, id DESC", params).fetchall()
    return render(request, "history.html", user=user, transactions=prepare_transactions(rows),
                  q=q, direction=direction)


@router.get("/profile")
def profile(request: Request, user=Depends(require_customer)):
    with get_conn() as conn:
        account = get_primary_account(conn, user["id"])
    tc = decrypt_field(user["tc_kimlik_enc"]) if user["tc_kimlik_enc"] else ""
    phone = decrypt_field(user["phone_enc"]) if user["phone_enc"] else ""
    return render(request, "profile.html", user=user,
                  masked_tc=mask_tc(tc) if tc else "-",
                  masked_phone=mask_phone(phone) if phone else "-",
                  masked_iban=mask_iban(account["iban_last4"]) if account else "-")
