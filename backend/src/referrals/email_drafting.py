"""
Drafts a referral-request email to a real contact discovered by
src/referrals/discovery.py, for a job the candidate just applied to.

Distinct in tone from src/outreach/engine.py's cold-outreach template
(generic "connecting" networking ask) -- this is framed around a real,
specific action already taken ("I just applied to X role") and a real,
narrow ask (a referral or a few minutes of their time), not a cold
introduction.
"""
import json

from src.system.logger import setup_logger
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient
from src.utils.llm_router import LLMRouter

logger = setup_logger("referral_email_drafting")

_PROMPT_TEMPLATE = """You are drafting a short, genuine referral-request email from a real
candidate to {contact_name}, who works at {company_name} (their role there:
{contact_role}). The candidate just submitted a real application for the
"{job_title}" role at {company_name} and is asking this person -- someone
they don't already know -- for a referral or a brief chat about the role.

Candidate background:
{profile_context}

Most relevant experience for this specific role:
{relevant_experience}

Write in first person as the candidate. Keep it short (under 120 words),
specific (reference the actual role and something concrete from their
background relevant to it), and honest that this is a cold ask -- do not
claim any prior connection to {contact_name} or {company_name} that isn't
true. No generic "I'd love to connect" filler. End with a clear, low-effort
ask (a referral, or 10 minutes to chat).

Return ONLY a JSON object: {{"subject": "...", "body": "..."}}
"""


def draft_referral_email(
    contact: dict,
    job_title: str,
    company_name: str,
    profile_manager: ProfileManager,
    rag_client: RAGClient,
    llm_client,
) -> tuple[str, str]:
    """Returns (subject, body). Raises on failure -- callers decide how to
    handle that (this module never silently returns a blank/placeholder
    email, since that would go out under the candidate's real name)."""
    full_name = f"{profile_manager.get_field('first_name') or ''} {profile_manager.get_field('last_name') or ''}".strip()
    profile_context = profile_manager.get_llm_context() or ""

    relevant_chunks = rag_client.retrieve(f"{job_title} {company_name}", top_k_initial=5, top_k_final=2)
    relevant_experience = "\n".join(c.get("text", "") for c in relevant_chunks) or "(no specific matching experience found)"

    prompt = _PROMPT_TEMPLATE.format(
        contact_name=contact.get("contact_name") or "there",
        company_name=company_name,
        contact_role=contact.get("job_title") or contact.get("contact_type") or "unknown role",
        job_title=job_title,
        profile_context=profile_context,
        relevant_experience=relevant_experience,
    )

    response = llm_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        response_format={"type": "json_object"},
        intent="referral_drafting",
    )
    data = json.loads(response.choices[0].message.content)
    subject = (data.get("subject") or "").strip()
    body = (data.get("body") or "").strip()
    if not subject or not body:
        raise ValueError(f"LLM returned an incomplete draft: {data}")

    # A signed, real name matters more here than in the auto-apply flow's
    # form-answers -- this goes into someone's inbox under the candidate's
    # identity. Append it if the model didn't already sign off with it.
    if full_name and full_name not in body:
        body = f"{body}\n\n{full_name}"

    return subject, body
