from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.auth import require_admin
from app.crypto import mask_iban
from app.db import get_conn
from app.routes import render
from app.routes.accounts import prepare_transactions

router = APIRouter(prefix="/admin")

LARGE_AMOUNT = 10_000 * 100
SUSPICIOUS_WORDS = ("<", "script", "talimat", "asistan", "ignore", "system", "transfer_money")


@router.get("")
def admin_home():
    return RedirectResponse("/admin/customers", status_code=303)


@router.get("/customers")
def customers(request: Request, user=Depends(require_admin)):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT u.id, u.username, u.full_name, u.role, u.locked_until, a.id AS account_id, "
            "a.iban_last4, a.balance, "
            "(SELECT COUNT(*) FROM transactions t WHERE t.account_id = a.id) AS tx_count "
            "FROM users u LEFT JOIN accounts a ON a.user_id = u.id "
            "WHERE u.role = 'customer' ORDER BY u.id"
        ).fetchall()
        tx_total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    customers = [dict(r, masked_iban=mask_iban(r["iban_last4"]) if r["iban_last4"] else "-") for r in rows]
    stats = {
        "customers": len(customers),
        "total_balance": sum(c["balance"] or 0 for c in customers),
        "locked": sum(1 for c in customers if c["locked_until"]),
        "transactions": tx_total,
    }
    return render(request, "admin_customers.html", user=user, customers=customers, stats=stats)


@router.get("/suspicious")
def suspicious(request: Request, user=Depends(require_admin)):
    word_filter = " OR ".join("LOWER(t.description) LIKE ?" for _ in SUSPICIOUS_WORDS)
    params = [f"%{w}%" for w in SUSPICIOUS_WORDS]
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT t.*, u.full_name AS owner FROM transactions t "
            "JOIN accounts a ON a.id = t.account_id JOIN users u ON u.id = a.user_id "
            f"WHERE ABS(t.amount) >= ? OR {word_filter} "
            "ORDER BY t.created_at DESC, t.id DESC LIMIT 200",
            [LARGE_AMOUNT, *params],
        ).fetchall()
        negative = conn.execute(
            "SELECT a.id, a.iban_last4, a.balance, u.full_name FROM accounts a "
            "JOIN users u ON u.id = a.user_id WHERE a.balance < 0"
        ).fetchall()
    return render(request, "admin_suspicious.html", user=user,
                  transactions=prepare_transactions(rows),
                  negative_accounts=[dict(r, masked_iban=mask_iban(r["iban_last4"])) for r in negative])
