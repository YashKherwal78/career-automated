"""
Generates a cover-letter PDF for the email-apply channel (EmailApplyAdapter).

Deliberately separate from auto_generate.py's generate_and_store_cover_letter:
that function always does a DB-tracked job_id lookup first (_resolve_jd_profile
checks `if request.job_id` before ever looking at job_description), which is
right for a real discovered posting but wrong here -- ingestion pipeline leads
(screenshot/email sourced) carry a synthetic uuid, not a job_id anything has
tracked, so a lookup against it would just fail. This always parses the JD
ad hoc from raw text (or falls back to a minimal profile if none was found)
and never persists a DB row, since a one-off outbound email attachment isn't
something later code needs to query back.
"""
import shutil
import tempfile
from typing import Optional

from src.system.logger import setup_logger

logger = setup_logger("cover_letter_for_email")


def generate_cover_letter_pdf(
    user_id: str,
    candidate_email: str,
    job_title: str,
    company_name: str,
    jd_text: str = "",
) -> Optional[str]:
    """Returns a PDF file path (in a temp dir the caller is responsible for
    cleaning up once the email has been sent/dry-run-logged), or None if the
    user isn't on a paid plan, there's no resume-fact profile to draw from,
    or generation failed for any reason -- always best-effort, never raises,
    since a missing cover letter should degrade to a resume-only email, not
    abort the whole apply attempt."""
    try:
        from src.billing.access import has_paid_access
        if not has_paid_access(user_id, candidate_email):
            logger.info(f"[cover_letter_for_email] user={user_id} not on paid plan, skipping cover letter")
            return None

        from src.api.db import get_connection
        from src.api.routers.tailor import _load_candidate_memory, _load_personal_info
        from src.resume_intelligence.cover_letter.generator import CoverLetterGenerator
        from src.resume_intelligence.cover_letter.models import CoverLetterInput
        from src.resume_intelligence.cover_letter.pdf_renderer import compile_pdf
        from src.resume_intelligence.job_intelligence.parser import JobDescriptionParser

        with get_connection() as conn:
            if jd_text.strip():
                import uuid
                jd_profile = JobDescriptionParser().parse_job_description(
                    job_id=f"adhoc-{uuid.uuid4().hex[:12]}",
                    company_name=company_name or "Unknown",
                    role_title=job_title or "the role",
                    raw_description=jd_text,
                ).model_dump()
            else:
                jd_profile = {"company_name": company_name, "role_title": job_title}

            candidate_memory = _load_candidate_memory(user_id, conn)
            personal_info = _load_personal_info(user_id, conn)

            generator = CoverLetterGenerator()
            result = generator.generate(CoverLetterInput(
                candidate_name=personal_info.get("full_name") or (candidate_email or "").split("@")[0],
                candidate_email=candidate_email,
                candidate_phone=personal_info.get("phone") or "",
                jd_profile=jd_profile,
                resume_facts=candidate_memory.get("global", []),
                company_name=company_name or "the company",
                role_title=job_title or "the role",
            ))

        if result.is_fallback or not result.cover_letter_tex:
            logger.info(f"[cover_letter_for_email] fallback/empty result for user={user_id}, skipping attachment")
            return None

        tmp_dir = tempfile.mkdtemp(prefix="email_apply_cover_letter_")
        pdf_path = compile_pdf(result.cover_letter_tex, tmp_dir, filename_prefix="cover_letter")
        if pdf_path is None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            logger.info(f"[cover_letter_for_email] PDF compilation failed for user={user_id}")
            return None
        return pdf_path
    except Exception as e:
        logger.info(f"[cover_letter_for_email] generation failed for user={user_id}: {e}")
        return None
