from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.db import get_connection, is_postgres
from src.outreach.email_client import EmailClient
from src.runtime.auth.dependencies import CurrentUser, get_current_user

router = APIRouter()


@router.get("/")
def list_referrals(current_user: CurrentUser = Depends(get_current_user)):
    """Drafted/sent referral emails for this user, most recent first --
    review queue for the PENDING_REVIEW ones."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT id, company_name, job_title, contact_name, contact_role, contact_email,
                   subject, body, status, error, created_at, sent_at
            FROM public.referral_outreach
            WHERE user_id = {ph}::uuid
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (current_user.user_id,),
        )
        rows = cur.fetchall()
    return {"items": [dict(r) if hasattr(r, "keys") else r for r in rows]}


@router.post("/{referral_id}/approve")
def approve_referral(referral_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Sends a PENDING_REVIEW draft now. This is the manual send path for
    while referral_auto_send is off -- "first few we check, then we
    automate" (once you're comfortable with draft quality, flip the policy
    instead of approving one at a time)."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT contact_email, subject, body, status FROM public.referral_outreach
            WHERE id = {ph}::uuid AND user_id = {ph}::uuid
            """,
            (referral_id, current_user.user_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Referral draft not found")
        d = row if isinstance(row, dict) else dict(row)
        if d["status"] != "PENDING_REVIEW":
            raise HTTPException(status_code=409, detail=f"Not pending review (status={d['status']})")

        try:
            EmailClient().send_email(d["contact_email"], d["subject"], d["body"])
        except Exception as e:
            conn.execute(
                f"UPDATE public.referral_outreach SET status = 'FAILED', error = {ph} WHERE id = {ph}::uuid",
                (str(e), referral_id),
            )
            conn.commit()
            raise HTTPException(status_code=502, detail=f"Send failed: {e}")

        conn.execute(
            f"UPDATE public.referral_outreach SET status = 'SENT', sent_at = NOW() WHERE id = {ph}::uuid",
            (referral_id,),
        )
        conn.commit()
    return {"status": "SENT"}


@router.post("/{referral_id}/reject")
def reject_referral(referral_id: str, current_user: CurrentUser = Depends(get_current_user)):
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            UPDATE public.referral_outreach SET status = 'REJECTED'
            WHERE id = {ph}::uuid AND user_id = {ph}::uuid AND status = 'PENDING_REVIEW'
            """,
            (referral_id, current_user.user_id),
        )
        conn.commit()
    return {"status": "REJECTED"}


class ReferralPolicy(BaseModel):
    auto_send: bool


@router.get("/policy")
def get_referral_policy(current_user: CurrentUser = Depends(get_current_user)):
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT referral_auto_send FROM public.user_application_policies WHERE user_id = {ph}::uuid",
            (current_user.user_id,),
        )
        row = cur.fetchone()
    if not row:
        return {"auto_send": False}
    d = row if isinstance(row, dict) else dict(row)
    return {"auto_send": bool(d.get("referral_auto_send"))}


@router.post("/policy")
def set_referral_policy(body: ReferralPolicy, current_user: CurrentUser = Depends(get_current_user)):
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        if is_postgres():
            conn.execute(
                f"""
                INSERT INTO public.user_application_policies (user_id, referral_auto_send, updated_at)
                VALUES ({ph}::uuid, {ph}, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET referral_auto_send = EXCLUDED.referral_auto_send, updated_at = NOW()
                """,
                (current_user.user_id, body.auto_send),
            )
        else:
            conn.execute(
                f"INSERT OR REPLACE INTO public.user_application_policies (user_id, referral_auto_send) VALUES ({ph}, {ph})",
                (current_user.user_id, body.auto_send),
            )
        conn.commit()
    return {"auto_send": body.auto_send}
