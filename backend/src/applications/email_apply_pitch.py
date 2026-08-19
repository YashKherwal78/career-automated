"""
Composes the email body for the "email your CV to jobs@company.com" apply
channel -- a post that gives no named contact, no ATS, just an address to
send a resume to. Reuses hr_referral_pitch.py's grounding/safety machinery
(real per-user profile facts, banned-phrase stripping, unsupported-number
retry+strip, familiarity-claim stripping) rather than duplicating it; the
only genuinely new piece is the prompt itself, since this addresses a
generic "Hiring Team" rather than a discovered contact and explicitly
mentions the resume/cover-letter attachments this channel always sends.
"""
import json
import re

from src.system.logger import setup_logger
from src.referrals.hr_referral_pitch import (
    _load_profile_facts,
    _strip_banned_phrases,
    _strip_familiarity_claims,
    _unsupported_numbers,
)

logger = setup_logger("email_apply_pitch")

_SYSTEM_PROMPT = """You write short, direct application emails from a real job candidate, sent to a \
generic hiring inbox (e.g. jobs@company.com) that a job post asked candidates to email their CV to \
directly -- there is no named recipient and no ATS/form for this posting.

STRICT OUTPUT: return ONLY a JSON object {{"subject": "...", "body": "..."}}. No markdown fences.

Subject line: state the job title and company only (e.g. "Application: Backend Engineer at Acme"). \
Never put a greeting or name in the subject.

Structure (3-4 sentences total in the body):
1. Open by stating plainly that you're applying for <job title> at <company>, addressed to "Hiring Team" \
or "Hello,"  -- not a fabricated named greeting.
2. One or two sentences connecting ONE or TWO specific, real, quantified achievements from the candidate \
background to why this role fits -- grounded only in the facts given below, never invented.
3. Close by noting the resume and cover letter are attached, and that you're happy to discuss further.

Hard rules:
- Target 60-90 words (body only), HARD CEILING 110.
- First person, direct, plain -- this reader has no context on you beyond this email and the attachments.
- BANNED WORDS -- do not use any of: passionate, excited, thrilled, great fit, cutting-edge, dynamic, \
synergy, team player.
- No "I hope this finds you well."
- Every factual claim about the CANDIDATE must trace to the candidate background below.
- Must explicitly mention that the resume and cover letter are attached -- this email always has both.
"""

_USER_TEMPLATE = """Role: {job_title} at {company_name}
Job description (if available): {jd_text}

Candidate background (only source of real facts/achievements -- use only these):
{resume_facts}

Write the email now."""


def draft_email_apply_pitch(
    job_title: str,
    company_name: str,
    jd_text: str,
    profile_manager,
    llm_client,
    user_id: str = "",
) -> tuple[str, str]:
    """Returns (subject, body). Raises ValueError on an incomplete LLM
    draft, same contract as draft_hr_or_referral_pitch -- never returns a
    blank/placeholder email since this goes out under the candidate's real
    name."""
    db_facts = _load_profile_facts(user_id) if user_id else []
    resume_facts = "\n".join(f"- {f}" for f in db_facts) or "(no specific matching experience found)"
    grounded_text = f"{resume_facts}\n{profile_manager.get_llm_context() or ''}"

    user_prompt = _USER_TEMPLATE.format(
        job_title=job_title, company_name=company_name,
        jd_text=jd_text or "(not available)", resume_facts=resume_facts,
    )

    def _generate() -> tuple[str, str]:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            response_format={"type": "json_object"},
            intent="referral_drafting",
        )
        data = json.loads(response.choices[0].message.content)
        subj = (data.get("subject") or "").strip()
        bod = (data.get("body") or "").strip()
        if not subj or not bod:
            raise ValueError(f"LLM returned an incomplete draft: {data}")
        return subj, bod

    subject, body = _generate()

    unsupported = _unsupported_numbers(body, grounded_text)
    if unsupported:
        logger.info(f"[email_apply_pitch] retry -- unsupported numbers in draft: {unsupported}")
        subject, body = _generate()
        unsupported = _unsupported_numbers(body, grounded_text)
        if unsupported:
            logger.info(f"[email_apply_pitch] still unsupported after retry: {unsupported}. Stripping.")
            for num in unsupported:
                body = re.sub(rf"[^.]*\b{re.escape(num)}\b[^.]*\.", "", body).strip()

    body = _strip_banned_phrases(body)
    subject = _strip_banned_phrases(subject)
    body = _strip_familiarity_claims(body)

    full_name = f"{profile_manager.get_field('first_name') or ''} {profile_manager.get_field('last_name') or ''}".strip()
    if full_name and full_name not in body:
        body = f"{body}\n\n{full_name}"

    return subject, body
