import shutil
from typing import Any, Dict

from src.applications.adapters.base_adapter import BaseAdapter, ApplicationResult
from src.applications.cover_letter_for_email import generate_cover_letter_pdf
from src.applications.email_apply_pitch import draft_email_apply_pitch
from src.outreach.email_client import EmailClient
from src.system.logger import setup_logger

logger = setup_logger("email_apply_adapter")


class EmailApplyAdapter(BaseAdapter):
    """The "email your CV to jobs@company.com" apply channel -- no browser,
    no DOM, unlike every other adapter in this system. Composes a pitch
    email, attaches the already-selected resume plus a best-effort cover
    letter, and sends via the existing outbound EmailClient. test_mode maps
    directly onto EmailClient's own dry_run flag, matching the dry-run-first
    convention every other connector already follows."""

    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router

    def apply(self, job: Dict[str, Any], resume_path: str, profile_manager: Any, test_mode: bool = False, user_id: str = None) -> ApplicationResult:
        to_email = job.get("apply_url", "")
        if not to_email:
            return ApplicationResult(status="REVIEW_REQUIRED", failure_reason="No email address to apply to")

        pm = profile_manager or self.profile_manager
        job_title = job.get("job_title", "")
        company_name = job.get("company_name", "")
        jd_text = job.get("description", "")
        candidate_email = (pm.get_field("email") if pm else "") or ""

        cover_letter_path = None
        try:
            subject, body = draft_email_apply_pitch(
                job_title=job_title, company_name=company_name, jd_text=jd_text,
                profile_manager=pm, llm_client=self.llm_router, user_id=user_id or "",
            )

            cover_letter_path = generate_cover_letter_pdf(
                user_id=user_id or "", candidate_email=candidate_email,
                job_title=job_title, company_name=company_name, jd_text=jd_text,
            )

            sent = EmailClient().send_email(
                to_email=to_email, subject=subject, body=body,
                resume_path=resume_path, extra_attachment_path=cover_letter_path,
                dry_run=test_mode,
            )

            return ApplicationResult(
                status="COMPLETED" if sent else "FAILED",
                confirmation_url="",
                screenshot_path="",
                submitted_answers={"to_email": to_email, "subject": subject, "body": body},
                failure_reason="" if sent else "EmailClient.send_email returned False",
                really_submitted=bool(sent and not test_mode),
            )
        except Exception as e:
            logger.info(f"[email_apply_adapter] failed to email {to_email}: {e}")
            return ApplicationResult(status="FAILED", failure_reason=str(e))
        finally:
            if cover_letter_path:
                import os
                shutil.rmtree(os.path.dirname(cover_letter_path), ignore_errors=True)
