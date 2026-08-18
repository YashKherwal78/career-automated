"""
Wires the (real, working) contact-discovery pipeline and the new
email-drafting module into an actual application: given a job someone just
applied to, find the best contact at that company, draft a referral email,
and store it in public.referral_outreach for review -- or send it
immediately if the user has turned on referral_auto_send.

Called from the apply flow (apply_service.py) as a best-effort side effect,
same convention as the embedding-update-on-profile-save pattern elsewhere:
a failure here must never fail or block the application itself.
"""
import json

from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres
from src.applications.profile import ProfileManager
from src.applications.rag import get_rag_client
from src.utils.llm_router import LLMRouter
from src.outreach.email_client import EmailClient
from src.referrals.pipeline import run_referral_engine
from src.referrals.email_drafting import draft_referral_email

logger = setup_logger("referral_apply_integration")


def _get_referral_auto_send(user_id: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT referral_auto_send FROM public.user_application_policies WHERE user_id = {ph}",
            (user_id,),
        )
        row = cur.fetchone()
    if not row:
        return False
    d = row if isinstance(row, dict) else dict(row)
    return bool(d.get("referral_auto_send"))


def _already_attempted(user_id: str, job_id: str) -> bool:
    if not job_id:
        return False
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT 1 FROM public.referral_outreach WHERE user_id = {ph}::uuid AND job_id = {ph}::uuid",
            (user_id, job_id),
        )
        return cur.fetchone() is not None


def _pick_best_contact(scored_contacts: list) -> dict | None:
    with_email = [c for c in scored_contacts if c.get("email")]
    if not with_email:
        return None
    with_email.sort(key=lambda c: c.get("referral_score", 0), reverse=True)
    return with_email[0]


def find_and_draft_referral(
    user_id: str,
    job_id: str,
    job_title: str,
    company_name: str,
    job_description: str = "",
    company_domain: str = "",
) -> None:
    if not company_name or not job_title:
        return
    if _already_attempted(user_id, job_id):
        return

    ph = "%s" if is_postgres() else "?"

    try:
        scored_contacts = run_referral_engine(company_name, job_title, job_description, company_domain) or []
        contact = _pick_best_contact(scored_contacts)
        if not contact:
            logger.info(f"[referral] no contact with an email found for {company_name} / {job_title}")
            return

        subject, body = draft_referral_email(
            contact=contact,
            job_title=job_title,
            company_name=company_name,
            profile_manager=ProfileManager(user_id=user_id),
            rag_client=get_rag_client(user_id=user_id),
            llm_client=LLMRouter(),
        )

        auto_send = _get_referral_auto_send(user_id)
        status = "PENDING_REVIEW"
        sent_at_clause = ""
        params = [
            user_id, job_id, company_name, job_title,
            contact.get("contact_name"), contact.get("job_title"), contact.get("email"),
            contact.get("email_confidence", 0), contact.get("discovery_source"),
            subject, body, status,
        ]

        if auto_send:
            try:
                EmailClient().send_email(contact["email"], subject, body)
                status = "SENT"
                sent_at_clause = ", sent_at = NOW()"
                params[11] = status
            except Exception as send_err:
                logger.info(f"[referral] send failed for {contact.get('email')}: {send_err}")
                status = "FAILED"
                params[11] = status

        with get_connection() as conn:
            conn.execute(
                f"""
                INSERT INTO public.referral_outreach
                    (user_id, job_id, company_name, job_title, contact_name, contact_role,
                     contact_email, email_confidence, discovery_source, subject, body, status{", sent_at" if sent_at_clause else ""})
                VALUES ({ph}::uuid, {ph}::uuid, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}{", NOW()" if sent_at_clause else ""})
                """,
                tuple(params),
            )
            conn.commit()

        logger.info(f"[referral] {status} draft for {contact.get('contact_name')} <{contact.get('email')}> ({company_name})")
    except Exception as e:
        logger.info(f"[referral] find_and_draft_referral failed (non-fatal): {e}")
