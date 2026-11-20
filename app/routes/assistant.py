from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.ai import agent
from app.auth import require_customer
from app.crypto import decrypt_field
from app.db import get_conn
from app.routes.transfers import execute_transfer, get_primary_account

router = APIRouter(prefix="/api/assistant")

DRAFT_TTL = timedelta(minutes=10)


class ChatIn(BaseModel):
    message: str


@router.post("/chat")
def chat(body: ChatIn, user=Depends(require_customer)):
    with get_conn() as conn:
        account = get_primary_account(conn, user["id"])
    if account is None:
        return JSONResponse({"reply": "Hesabınız bulunamadı."}, status_code=400)
    result = agent.chat(user, account["id"], body.message)
    return {"reply": result.reply, "drafts": result.drafts, "tool_calls": result.tool_calls}


@router.post("/reset")
def reset(user=Depends(require_customer)):
    agent.clear_history(user["id"])
    return {"ok": True}


@router.post("/drafts/{draft_id}/confirm")
def confirm_draft(draft_id: int, user=Depends(require_customer)):
    with get_conn() as conn:
        draft = conn.execute(
            "SELECT * FROM transfer_drafts WHERE id = ? AND user_id = ?", (draft_id, user["id"])
        ).fetchone()
        if draft is None:
            return JSONResponse({"ok": False, "message": "Taslak bulunamadı."}, status_code=404)

        created = datetime.fromisoformat(draft["created_at"]).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > DRAFT_TTL:
            conn.execute("UPDATE transfer_drafts SET status = 'expired' WHERE id = ? AND status = 'pending'",
                         (draft_id,))
            return JSONResponse({"ok": False, "message": "Taslağın süresi doldu."}, status_code=410)

        # claim the draft first so a double click can't send the money twice
        claimed = conn.execute(
            "UPDATE transfer_drafts SET status = 'processing' WHERE id = ? AND status = 'pending'", (draft_id,)
        ).rowcount
        if claimed != 1:
            return JSONResponse({"ok": False, "message": "Bu taslak zaten işlendi."}, status_code=409)

        ok, message = execute_transfer(conn, draft["from_account_id"], decrypt_field(draft["to_iban_enc"]),
                                       draft["amount"], draft["description"] or "Asistan ile transfer")
        conn.execute("UPDATE transfer_drafts SET status = ? WHERE id = ?",
                     ("done" if ok else "failed", draft_id))
    return JSONResponse({"ok": ok, "message": message}, status_code=200 if ok else 400)


@router.post("/drafts/{draft_id}/cancel")
def cancel_draft(draft_id: int, user=Depends(require_customer)):
    with get_conn() as conn:
        n = conn.execute(
            "UPDATE transfer_drafts SET status = 'cancelled' WHERE id = ? AND user_id = ? AND status = 'pending'",
            (draft_id, user["id"]),
        ).rowcount
    return {"ok": n == 1, "message": "Taslak iptal edildi." if n == 1 else "Taslak bulunamadı."}
