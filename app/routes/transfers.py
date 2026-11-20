import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import require_customer
from app.config import settings
from app.crypto import iban_index, normalize_iban
from app.db import get_conn
from app.routes import format_money, parse_amount, render

router = APIRouter()

MAX_TRANSFER_KURUS = 50_000 * 100
MAX_DESCRIPTION = 140


def get_primary_account(conn: sqlite3.Connection, user_id: int):
    return conn.execute(
        "SELECT * FROM accounts WHERE user_id = ? ORDER BY id LIMIT 1", (user_id,)
    ).fetchone()


def find_account_by_iban(conn: sqlite3.Connection, iban: str):
    return conn.execute(
        "SELECT a.*, u.full_name FROM accounts a JOIN users u ON u.id = a.user_id "
        "WHERE a.iban_index = ?",
        (iban_index(iban),),
    ).fetchone()


def _record(conn, sender, receiver, sender_name, amount, description):
    conn.execute(
        "INSERT INTO transactions (account_id, counterparty_name, counterparty_last4, amount, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (sender["id"], receiver["full_name"], receiver["iban_last4"], -amount, description),
    )
    conn.execute(
        "INSERT INTO transactions (account_id, counterparty_name, counterparty_last4, amount, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (receiver["id"], sender_name, sender["iban_last4"], amount, description),
    )


def execute_transfer(conn: sqlite3.Connection, from_account_id: int, to_iban: str,
                     amount: int, description: str) -> tuple[bool, str]:
    sender = conn.execute(
        "SELECT a.*, u.full_name FROM accounts a JOIN users u ON u.id = a.user_id WHERE a.id = ?",
        (from_account_id,),
    ).fetchone()
    receiver = find_account_by_iban(conn, to_iban)
    if sender is None:
        return False, "Gönderen hesap bulunamadı."
    if receiver is None:
        return False, "Alıcı IBAN bulunamadı."

    # VULN-04: no amount/balance validation, read-modify-write outside a transaction | OWASP: A04:2021 Insecure Design
    if settings.SECURE_MODE:
        if receiver["id"] == sender["id"]:
            return False, "Kendi hesabınıza transfer yapamazsınız."
        if amount <= 0:
            return False, "Tutar sıfırdan büyük olmalı."
        if amount > MAX_TRANSFER_KURUS:
            return False, f"Tek seferde en fazla {format_money(MAX_TRANSFER_KURUS)} gönderebilirsiniz."
        description = description[:MAX_DESCRIPTION]

        conn.execute("BEGIN IMMEDIATE")
        try:
            # balance check and debit in one statement, so two parallel requests can't both pass
            cur = conn.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ?",
                (amount, sender["id"], amount),
            )
            if cur.rowcount != 1:
                conn.execute("ROLLBACK")
                return False, "Yetersiz bakiye."
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, receiver["id"]))
            _record(conn, sender, receiver, sender["full_name"], amount, description)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    else:
        conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (sender["balance"] - amount, sender["id"]))
        conn.execute("UPDATE accounts SET balance = ? WHERE id = ?", (receiver["balance"] + amount, receiver["id"]))
        _record(conn, sender, receiver, sender["full_name"], amount, description)

    return True, f"{receiver['full_name']} adlı alıcıya {format_money(amount)} gönderildi."


@router.get("/transfer")
def transfer_form(request: Request, user=Depends(require_customer)):
    return render(request, "transfer.html", user=user)


@router.post("/transfer")
def transfer_submit(request: Request, user=Depends(require_customer),
                    to_iban: str = Form(...), amount: str = Form(...), description: str = Form("")):
    kurus = parse_amount(amount)
    if kurus is None:
        return render(request, "transfer.html", user=user, error="Geçersiz tutar.",
                      form={"to_iban": to_iban, "amount": amount, "description": description})

    with get_conn() as conn:
        account = get_primary_account(conn, user["id"])
        ok, message = execute_transfer(conn, account["id"], normalize_iban(to_iban), kurus, description)

    if not ok:
        return render(request, "transfer.html", user=user, error=message,
                      form={"to_iban": to_iban, "amount": amount, "description": description})
    request.session["flash"] = message
    return RedirectResponse("/hesabim", status_code=303)
