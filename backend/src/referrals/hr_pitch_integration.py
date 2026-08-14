"""
Orchestrates the second outreach system (src/referrals/hr_referral_pitch.py)
into an actual application, the same way apply_integration.py wires up the
original cold-referral-ask system -- reuses that module's contact-discovery
call and a couple of its small read-only helpers rather than duplicating
them, but never modifies apply_integration.py or email_drafting.py.

Called as a best-effort side effect from the same trigger points as
find_and_draft_referral -- a failure here must never affect the
application itself, and this and the original system both run
independently per real application (two separate emails: one from each
system, stored in two separate tables).
"""
from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter
from src.outreach.email_client import EmailClient
from src.referrals.pipeline import run_referral_engine
from src.referrals.hr_referral_pitch import draft_hr_or_referral_pitch
from src.referrals.apply_integration import _get_referral_auto_send, _pick_best_contact

logger = setup_logger("hr_pitch_integration")


def _already_attempted(user_id: str, job_id: str) -> bool:
    if not job_id:
        return False
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT 1 FROM public.hr_referral_pitches WHERE user_id = {ph}::uuid AND job_id = {ph}::uuid",
            (user_id, job_id),
        )
        return cur.fetchone() is not None


def find_and_draft_hr_pitch(
    user_id: str,
    job_id: str,
    job_title: str,
    company_name: str,
    job_description: str = "",
    company_domain: str = "",
    apply_url: str = "",
) -> None:
    """Best-effort, non-fatal -- same contract as find_and_draft_referral.
    Reuses that module's auto-send policy check and best-contact picker
    (both are small, read-only, and duplicating them would just create two
    copies to keep in sync for no benefit)."""
    ph = "%s" if is_postgres() else "?"
    try:
        if _already_attempted(user_id, job_id):
            return

        scored_contacts = run_referral_engine(company_name, job_title, job_description, company_domain) or []
        contact = _pick_best_contact(scored_contacts)
        if not contact:
            logger.info(f"[hr_pitch] no contact with an email found for {company_name} / {job_title}")
            return

        subject, body, mail_type = draft_hr_or_referral_pitch(
            contact=contact,
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            profile_manager=ProfileManager(user_id=user_id),
            rag_client=RAGClient(),
            llm_client=LLMRouter(),
            apply_url=apply_url,
            user_id=user_id,
        )

        auto_send = _get_referral_auto_send(user_id)
        status = "PENDING_REVIEW"
        sent_at_clause = ""
        params = [
            user_id, job_id, company_name, job_title,
            contact.get("contact_name"), contact.get("job_title"), contact.get("email"),
            contact.get("email_confidence", 0), contact.get("discovery_source"),
            mail_type, subject, body, status,
        ]

        if auto_send:
            try:
                EmailClient().send_email(contact["email"], subject, body)
                status = "SENT"
                sent_at_clause = ", sent_at = NOW()"
                params[12] = status
            except Exception as send_err:
                logger.info(f"[hr_pitch] send failed for {contact.get('email')}: {send_err}")
                status = "FAILED"
                params[12] = status

        with get_connection() as conn:
            conn.execute(
                f"""
                INSERT INTO public.hr_referral_pitches
                    (user_id, job_id, company_name, job_title, contact_name, contact_role,
                     contact_email, email_confidence, discovery_source, mail_type, subject, body, status{", sent_at" if sent_at_clause else ""})
                VALUES ({ph}::uuid, {ph}::uuid, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}{", NOW()" if sent_at_clause else ""})
                """,
                tuple(params),
            )
            conn.commit()

        logger.info(f"[hr_pitch] {status} ({mail_type}) draft for {contact.get('contact_name')} <{contact.get('email')}> ({company_name})")
    except Exception as e:
        logger.info(f"[hr_pitch] failed for user={user_id} job={job_id}: {e}")
