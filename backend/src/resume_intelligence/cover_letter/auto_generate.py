"""
Cover-letter generation as a real-application side effect, for paid-tier
users only -- mirrors src/referrals/apply_integration.py's
find_and_draft_referral: best-effort, non-fatal, called after a real
(non-test-mode) submission with the same job-dict fields batch_apply.py's
candidate query already has, no extra DB round-trip needed for the JD.

Reuses tailor.py's private JD-resolution/candidate-facts helpers rather
than duplicating that logic -- both call sites (the HTTP endpoint and this
one) need the exact same "load base facts, parse or look up the JD" step.
"""
from src.system.logger import setup_logger

logger = setup_logger("cover_letter_auto_generate")


def generate_and_store_cover_letter(
    user_id: str,
    email: str,
    job_id: str,
    job_title: str,
    company_name: str,
    job_description: str = "",
) -> None:
    """Best-effort: logs and returns on any failure rather than raising,
    since this runs after a real submission has already succeeded and must
    never affect that outcome. Paid-tier gate checked here (not just at
    the HTTP endpoint) since this call site has no request/current_user to
    gate through FastAPI's dependency system."""
    try:
        from src.billing.access import has_paid_access
        if not has_paid_access(user_id, email):
            return

        from src.api.db import get_connection, is_postgres
        from src.api.routers.tailor import (
            TailorRequest,
            _load_ai_preferences,
            _load_candidate_memory,
            _resolve_jd_profile,
        )
        from src.resume_intelligence.cover_letter.generator import CoverLetterGenerator
        from src.resume_intelligence.cover_letter.models import CoverLetterInput

        with get_connection() as conn:
            tailor_request = TailorRequest(
                candidate_id=user_id,
                job_id=job_id,
                job_description=job_description or None,
                company_name=company_name,
                role_title=job_title,
            )
            effective_job_id, jd_profile = _resolve_jd_profile(tailor_request, conn)
            candidate_memory = _load_candidate_memory(user_id, conn)
            writing_tone, _ = _load_ai_preferences(user_id, conn)

            generator = CoverLetterGenerator()
            result = generator.generate(CoverLetterInput(
                candidate_name=(email or "").split("@")[0],
                candidate_email=email,
                jd_profile=jd_profile,
                resume_facts=candidate_memory.get("global", []),
                company_name=company_name or jd_profile.get("company_name") or "the company",
                role_title=job_title or jd_profile.get("role_title") or "the role",
                writing_tone=writing_tone,
            ))
            if result.is_fallback:
                logger.info(f"[cover_letter] fallback result for user={user_id} job={job_id}, not storing.")
                return

            ph = "%s" if is_postgres() else "?"
            conn.execute(
                f"""
                INSERT INTO public.generated_cover_letters
                    (user_id, job_id, company_name, job_title, cover_letter_text, word_count)
                VALUES ({ph}::uuid, {ph}::uuid, {ph}, {ph}, {ph}, {ph})
                ON CONFLICT (user_id, job_id) DO UPDATE SET
                    cover_letter_text = EXCLUDED.cover_letter_text,
                    word_count = EXCLUDED.word_count,
                    company_name = EXCLUDED.company_name,
                    job_title = EXCLUDED.job_title,
                    created_at = NOW()
                """,
                (user_id, effective_job_id, company_name, job_title, result.cover_letter_text, result.word_count),
            )
            conn.commit()
            logger.info(f"[cover_letter] generated + stored for user={user_id} job={effective_job_id}")
    except Exception as e:
        logger.info(f"[cover_letter] generation failed for user={user_id} job={job_id}: {e}")
