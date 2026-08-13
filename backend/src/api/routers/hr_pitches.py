"""
API surface for the second outreach system (src/referrals/hr_referral_pitch.py,
src/referrals/hr_pitch_integration.py). Mirrors referrals.py's list/approve/
reject shape but is a fully separate router/table -- referrals.py itself is
untouched.
"""
from fastapi import APIRouter, Depends, HTTPException

from src.api.db import get_connection, is_postgres
from src.outreach.email_client import EmailClient
from src.runtime.auth.dependencies import CurrentUser, get_current_user

router = APIRouter()


@router.get("/")
def list_hr_pitches(current_user: CurrentUser = Depends(get_current_user)):
    """Drafted/sent HR-pitch and referral-ask emails for this user, most
    recent first. Each row's mail_type ("hr_pitch" or "referral_ask") tells
    the UI which flavor it is."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT id, company_name, job_title, contact_name, contact_role, contact_email,
                   mail_type, subject, body, status, error, created_at, sent_at
            FROM public.hr_referral_pitches
            WHERE user_id = {ph}::uuid
            ORDER BY created_at DESC
            LIMIT 100
            """,
            (current_user.user_id,),
        )
        rows = cur.fetchall()
    return {"items": [dict(r) if hasattr(r, "keys") else r for r in rows]}


@router.post("/{pitch_id}/approve")
def approve_hr_pitch(pitch_id: str, current_user: CurrentUser = Depends(get_current_user)):
    """Sends a PENDING_REVIEW draft now -- same manual-send path as
    referrals.py's approve endpoint, same reasoning: review each one until
    you trust the quality, then flip the (shared) auto-send policy."""
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT contact_email, subject, body, status FROM public.hr_referral_pitches
            WHERE id = {ph}::uuid AND user_id = {ph}::uuid
            """,
            (pitch_id, current_user.user_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Draft not found")
        d = row if isinstance(row, dict) else dict(row)
        if d["status"] != "PENDING_REVIEW":
            raise HTTPException(status_code=409, detail=f"Not pending review (status={d['status']})")

        try:
            EmailClient().send_email(d["contact_email"], d["subject"], d["body"])
        except Exception as e:
            conn.execute(
                f"UPDATE public.hr_referral_pitches SET status = 'FAILED', error = {ph} WHERE id = {ph}::uuid",
                (str(e), pitch_id),
            )
            conn.commit()
            raise HTTPException(status_code=502, detail=f"Send failed: {e}")

        conn.execute(
            f"UPDATE public.hr_referral_pitches SET status = 'SENT', sent_at = NOW() WHERE id = {ph}::uuid",
            (pitch_id,),
        )
        conn.commit()
    return {"status": "SENT"}


@router.post("/{pitch_id}/reject")
def reject_hr_pitch(pitch_id: str, current_user: CurrentUser = Depends(get_current_user)):
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        conn.execute(
            f"""
            UPDATE public.hr_referral_pitches SET status = 'REJECTED'
            WHERE id = {ph}::uuid AND user_id = {ph}::uuid AND status = 'PENDING_REVIEW'
            """,
            (pitch_id, current_user.user_id),
        )
        conn.commit()
    return {"status": "REJECTED"}
