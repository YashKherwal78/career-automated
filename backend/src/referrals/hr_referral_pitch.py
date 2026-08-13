"""
A second, distinct outreach email writer -- separate from email_drafting.py
(untouched, still used for the original generic "I just applied, could you
refer me" cold ask). This one branches on who the discovered contact
actually is (contact_type from discovery.py: "Recruiter" / "Hiring Manager"
/ "Technical IC"):

- Recruiter / Hiring Manager -> a direct fit pitch: candidate background
  vs. this specific job, referencing the job by its real posting so the
  reader has something concrete to act on. They can move on this
  themselves, so the ask is "consider me", not "refer me".
- Technical IC (a peer in a similar role, often more senior) -> a referral
  ask, not a fit pitch -- they usually can't hire directly, so pitching
  "fit" at them is the wrong ask. Structured per the low-effort-ask
  research this was built against (see REFERRAL_ASK_SYSTEM_PROMPT):
  personalize, state role+company plainly, ask for one small, easy-to-say-
  yes-to thing (forward the resume, or a 15-min chat), give them an easy
  out.

Research backing both structures (see commit message for full sources):
- Cold email response rate roughly doubles with genuine personalization;
  under ~125 words consistently outperforms longer emails.
- Referral asks specifically convert better when the ask is small and
  low-effort ("forward this" / "15 minutes"), not a big commitment, and
  when the message explicitly gives the recipient an easy way to decline
  without feeling bad about it -- removes the social cost of ignoring it.
- The bulleted, specific-achievement structure (numbers instead of
  adjectives) is adapted from a real, previously-used cold-outreach
  template of this candidate's (research/Auto-mail-all-branches) rather
  than invented from scratch.
"""
import json
import re

from src.system.logger import setup_logger
from src.applications.profile import ProfileManager
from src.applications.rag import RAGClient

logger = setup_logger("hr_referral_pitch")

# The candidate background these emails were actually drawing from was
# RAGClient's static, hardcoded yash_master_profile.md file -- a fixed
# markdown file, not this user's real database profile. Confirmed real
# quality gap, not just a correctness/multi-tenancy one: the real
# per-user profile (public.user_career_profiles, written by the Career
# Profile page) had richer, more current bullet points that the static
# file didn't (a "Nexus" and "Sentinel" project, and materially more
# up-to-date metrics on "CareerAutomated" itself) that were never being
# used. This loads real, structured, quantified bullets straight from
# that DB row -- the actual "candidate profile" -- and only falls back
# to the RAG file if a user hasn't filled in a profile yet (keeps this
# working for a brand-new user with an empty database profile).
def _load_profile_facts(user_id: str, max_facts: int = 10) -> list[str]:
    try:
        from src.api.db import get_connection
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT profile_data FROM public.user_career_profiles WHERE user_id = %s LIMIT 1",
                (user_id,),
            )
            row = cursor.fetchone()
        if not row:
            return []
        profile_data = row["profile_data"] if hasattr(row, "keys") else row[0]
        if not profile_data:
            return []
        profile = json.loads(profile_data) if isinstance(profile_data, str) else profile_data

        facts: list[str] = []
        for exp in (profile.get("experience") or []):
            role = exp.get("role") or exp.get("title") or ""
            company = exp.get("company") or ""
            prefix = f"At {company} ({role}): " if (role or company) else ""
            for bullet in (exp.get("bullet_points") or []):
                if bullet:
                    facts.append(f"{prefix}{bullet}")
            for achievement in (exp.get("achievements") or []):
                if achievement:
                    facts.append(f"{prefix}{achievement}")

        for proj in (profile.get("projects") or []):
            name = proj.get("name") or ""
            prefix = f"Project {name}: " if name else ""
            for bullet in (proj.get("bullet_points") or []):
                if bullet:
                    facts.append(f"{prefix}{bullet}")

        for achievement in (profile.get("achievements") or []):
            if isinstance(achievement, str) and achievement:
                facts.append(achievement)

        return facts[:max_facts]
    except Exception as e:
        logger.info(f"_load_profile_facts failed for user_id={user_id}: {e}")
        return []

HR_PITCH_SYSTEM_PROMPT = """You write short, specific outreach emails from a real job candidate directly \
to a recruiter or hiring manager at the company they just applied to.

STRICT OUTPUT: return ONLY a JSON object {{"subject": "...", "body": "..."}}. No markdown fences.

Subject line: state the job title and company only (e.g. "Application for Software Engineer at Razorpay"). \
NEVER put a greeting, name, or "Hi <name>" inside the subject -- that belongs in the body only.

Structure (follow this EXACT shape -- the bullet points are not optional \
prose, they must be literal lines starting with the "•" character):

I just applied for the <Job Title> role at <Company>. <ONE short clause, under 12 words, on why this role caught \
your eye -- do not restate your whole background here, that's what the bullets are for.>

A few things from my background that I think are directly relevant:
• **At <Company/Project 1>,** <ONE specific, quantified achievement -- one sentence, under 20 words>.
• **At <Company/Project 2>,** <ONE specific, quantified achievement -- one sentence, under 20 words>.

<ONE closing sentence, under 20 words, that is ONLY the ask -- do not re-summarize the bullets here, that's \
redundant and the #1 cause of these drafts running long. Ask directly to be considered or for a quick chat -- \
this person can act on the application themselves, so the ask is "consider me," not "refer me.">

This is FOUR lines total: opener, bullet, bullet, closing ask. Nothing else. EXACTLY 2 bullets, never 3. Each \
bullet is ONE sentence. A third bullet, a two-sentence bullet, or a closing line that re-explains the bullets \
will always push you over 130 words -- do not do any of those no matter how well it seems to fit.

Hard rules:
- Each of the 4 lines (opener, bullet 1, bullet 2, closing) is separated by a literal newline character in the \
JSON string value -- your "body" field must contain actual \\n characters between them, with a blank line \
(\\n\\n) before the closing sentence. Do not run them together as one paragraph.
- Bullets MUST use the "•" character followed by "**<Company/Project>,**" in bold, exactly like the shape above, \
each on its own line with a blank line before the closing sentence.
- Target 90-100 words (body only), HARD CEILING 130 -- drafts have consistently run 25-45 words over target \
by re-explaining the bullets in the closing line. Do not do that -- the closing line is the ask, nothing else.
- First person ("I built...", never "the candidate...").
- BANNED WORDS -- do not use any of: passionate, excited, thrilled, great fit, cutting-edge, dynamic, synergy, \
team player. If you catch yourself about to write one of these, replace it with a plain factual statement \
instead (e.g. not "I'm excited about this role" but "This role is the kind of problem I want to be solving").
- No "I hope this email finds you well," no generic filler.
- Every claim must trace to the candidate background given below -- if a number isn't there, don't state one. \
Never invent a bullet not grounded in that background.
- Tone: direct, confident, specific.
"""

HR_PITCH_USER_TEMPLATE = """Recipient: {contact_name}, {contact_role} at {company_name}
Role applied to: {job_title} at {company_name}

Candidate background (only source of real facts/achievements -- use only these):
{resume_facts}

Write the email now."""

REFERRAL_ASK_SYSTEM_PROMPT = """You write short, low-pressure emails from a real job candidate to someone \
who works in a similar role (often more senior) at a company the candidate just applied to. This person \
is a peer, not a recruiter -- they likely can't hire directly, so the ask is for a referral or a forward, \
not "consider me for the role."

STRICT OUTPUT: return ONLY a JSON object {{"subject": "...", "body": "..."}}. No markdown fences.

Subject line: state the job title and company only (e.g. "AI Engineer role at Zomato" or "Quick question re: \
AI Engineer opening"). NEVER put a greeting, name, or "Hi <name>" inside the subject -- that belongs in the \
body only.

Structure (follow exactly, 5 sentences total in the body):
1. A brief, honest opener naming their role/seniority at the company (e.g. "as someone senior on the \
<company> engineering team"). Do NOT claim to have read their posts, blog, profile, or any specific work of \
theirs unless that exact detail is given to you below -- if nothing like that is provided, keep the opener to \
their role/title only. An invented "I saw your work on X" is worse than a plain opener; never do it. This \
sentence and sentence 2 must not both separately state that you applied -- combine the two into one clause \
if needed (e.g. "...I wanted to reach out since I just applied for <job title>.").
2. State plainly: you just applied for <job title> at <company> -- ONLY if not already covered in sentence 1.
3. One sentence connecting ONE specific, real achievement from the candidate background to why this role fits.
4. The ask: a single small, low-effort thing -- forwarding the resume to the right person, or a brief 15-minute \
chat. Use exactly "15-minute" if you mention a call length -- never invent a different number. Never ask for \
more than one thing.
5. An explicit, genuine easy-out: acknowledge they're likely busy and it's completely fine if they can't help. \
This sentence is MANDATORY, not optional -- a draft with 4 sentences and no easy-out is an incomplete draft. \
Example shape: "No worries at all if you don't have the bandwidth -- I know things get busy."

Hard rules:
- The body MUST contain all 5 numbered elements above, including the easy-out in point 5. Check before \
returning: does the last sentence explicitly say it's okay if they can't help? If not, add it.
- Target 75-85 words (body only), HARD CEILING 100 -- this is a peer ask, brevity matters more here than in a \
recruiter pitch. Drafts have consistently run over target -- aim short, cut a clause before you'd go over.
- First person, direct.
- BANNED WORDS -- do not use any of: passionate, excited, thrilled, great fit, cutting-edge, dynamic, synergy, \
team player. This includes "I'm excited about the opportunity" and every close variant of it. If you catch \
yourself about to write one of these, replace it with a plain factual statement instead (e.g. not "I'm excited \
about Zomato's AI work" but "Zomato's AI work is the kind of problem I want to be solving").
- No "I hope this finds you well."
- Every factual claim about the CANDIDATE must trace to the candidate background below. (The "15-minute chat" \
ask itself is not a factual claim about the candidate -- it's fine to include.)
- Do not claim any prior connection to this person that isn't true -- this is a cold ask, be honest about that.
- Tone: respectful, low-pressure, specific.
- Include all 5 structural elements -- do not skip the easy-out or the specific ask.
"""

REFERRAL_ASK_USER_TEMPLATE = """Recipient: {contact_name}, {contact_role} at {company_name}
Role applied to: {job_title} at {company_name}

Candidate background (only source of real facts/achievements -- use only these):
{resume_facts}

Write the email now."""

# Prompt instructions alone don't reliably suppress these -- confirmed
# real: "I'm excited about..." kept reappearing across regenerations
# despite an explicit, repeated ban in the system prompt. This is a
# programmatic safety net on top of the prompt rule, not a replacement for
# it: strip/replace on the actual generated text rather than trust
# instruction-following alone.
_BANNED_PHRASES = [
    (r"\bi'?m excited (about|to)\b", "I'm looking forward to"),
    (r"\bi am excited (about|to)\b", "I am looking forward to"),
    (r"\bpassionate about\b", "focused on"),
    (r"\bgreat fit\b", "a strong match"),
    (r"\bcutting-edge\b", "modern"),
    (r"\bdynamic\b", ""),
    (r"\bsynergy\b", "overlap"),
    (r"\bteam player\b", "collaborative"),
]


def _strip_banned_phrases(text: str) -> str:
    for pattern, replacement in _BANNED_PHRASES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", text).strip()


def _fix_bullet_formatting(body: str) -> str:
    """The hr_pitch template asks for each bullet on its own line, with a
    blank line before the closing sentence -- confirmed real that the LLM
    doesn't reliably do this on its own even when told explicitly, running
    the opener/bullets/closing together as one paragraph. Deterministic
    fallback: force a newline before every "•" and before the sentence
    that follows the last one, rather than depend on prompt compliance for
    something this mechanical."""
    if "•" not in body:
        return body
    # Newline before every bullet marker.
    body = re.sub(r"\s*•", "\n•", body)
    # Blank line between the last bullet's sentence and whatever follows
    # it on the same line (the closing ask, if the model ran it on).
    body = re.sub(r"(•[^\n]*?\.)\s+(?!•)([A-Z])", r"\1\n\n\2", body)
    return body.strip()


# Whole-sentence removal, not word substitution -- these are fabricated
# claims of familiarity with the recipient specifically (no real per-
# contact bio data is available to this pipeline today -- scrape_profile()
# in profile_intelligence.py is a hardcoded mock, confirmed while building
# this), so there's no way to "fix" one of these into a true statement.
# The prompt explicitly bans them and mostly complies, but not reliably --
# confirmed real across repeated generations against live contacts.
_FAMILIARITY_CLAIM_PATTERNS = [
    r"i'?ve been following your work",
    r"i saw your (post|profile|work|blog)",
    r"i read your (post|profile|work|blog)",
    r"came across your (post|profile|work|blog)",
    r"impressed by (your|the work you)",
    r"i noticed your (post|profile|work)",
]
_FAMILIARITY_CLAIM_RE = re.compile("|".join(_FAMILIARITY_CLAIM_PATTERNS), re.IGNORECASE)


def _strip_familiarity_claims(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = [s for s in sentences if not _FAMILIARITY_CLAIM_RE.search(s)]
    return re.sub(r"\s{2,}", " ", " ".join(kept)).strip()


_HR_CONTACT_TYPES = {"recruiter", "hiring manager"}


def _mode_for_contact(contact: dict) -> str:
    contact_type = (contact.get("contact_type") or "").strip().lower()
    return "hr_pitch" if contact_type in _HR_CONTACT_TYPES else "referral_ask"


# Common meeting-length numbers the ask itself is allowed to use (e.g. "a
# 15-minute chat") -- these are scheduling convention, not a factual claim
# about the candidate, so they shouldn't trip the same grounding check that
# catches an invented achievement metric. Confirmed real bug otherwise: the
# first version of this check stripped the sentence containing the
# instructed "15-minute" ask, silently deleting the email's actual call to
# action.
_ALLOWED_UNGROUNDED_NUMBERS = {"5", "10", "15", "20", "30"}


def _unsupported_numbers(body: str, grounded_text: str) -> set[str]:
    grounded_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", grounded_text))
    body_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", body))
    return body_nums - grounded_nums - _ALLOWED_UNGROUNDED_NUMBERS


def draft_hr_or_referral_pitch(
    contact: dict,
    job_id: str,
    job_title: str,
    company_name: str,
    profile_manager: ProfileManager,
    rag_client: RAGClient,
    llm_client,
    apply_url: str = "",
    user_id: str = "",
) -> tuple[str, str, str]:
    """Returns (subject, body, mode) where mode is "hr_pitch" or
    "referral_ask" -- callers store this so the Outreach UI can label which
    kind of email each draft is. Raises on failure, same contract as
    email_drafting.draft_referral_email -- never returns a blank/placeholder
    email since this goes out under the candidate's real name."""
    mode = _mode_for_contact(contact)
    logger.info(f"[{mode}] drafting for job_id={job_id} contact={contact.get('contact_name')} ({contact.get('contact_type')})")
    contact_name = contact.get("contact_name") or "there"
    contact_role = contact.get("job_title") or contact.get("contact_type") or "unknown role"

    # Real per-user database profile first (see _load_profile_facts) --
    # richer and more current than the static RAG file. Falls back to the
    # RAG file only if this user hasn't filled in a profile yet.
    db_facts = _load_profile_facts(user_id) if user_id else []
    if db_facts:
        resume_facts = "\n".join(f"- {f}" for f in db_facts)
        logger.info(f"[{mode}] using {len(db_facts)} facts from database candidate profile")
    else:
        query = f"{job_title} {company_name}"
        chunks = rag_client.retrieve(query, top_k_initial=8, top_k_final=4)
        resume_facts = "\n".join(f"- {c.get('text', '')}" for c in chunks) or "(no specific matching experience found)"
        logger.info(f"[{mode}] no database profile facts -- falling back to RAG file")
    grounded_text = f"{resume_facts}\n{profile_manager.get_llm_context() or ''}"

    if mode == "hr_pitch":
        system_prompt = HR_PITCH_SYSTEM_PROMPT
        user_prompt = HR_PITCH_USER_TEMPLATE.format(
            contact_name=contact_name,
            contact_role=contact_role,
            company_name=company_name,
            job_title=job_title,
            resume_facts=resume_facts,
        )
    else:
        system_prompt = REFERRAL_ASK_SYSTEM_PROMPT
        user_prompt = REFERRAL_ASK_USER_TEMPLATE.format(
            contact_name=contact_name,
            contact_role=contact_role,
            company_name=company_name,
            job_title=job_title,
            resume_facts=resume_facts,
        )

    def _generate() -> tuple[str, str]:
        response = llm_client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
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
        logger.info(f"[{mode}] Retry -- unsupported numbers in draft: {unsupported}")
        subject, body = _generate()
        unsupported = _unsupported_numbers(body, grounded_text)
        if unsupported:
            logger.info(f"[{mode}] Still unsupported after retry: {unsupported}. Stripping.")
            for num in unsupported:
                body = re.sub(rf"[^.]*\b{re.escape(num)}\b[^.]*\.", "", body).strip()

    body = _strip_banned_phrases(body)
    subject = _strip_banned_phrases(subject)
    body = _strip_familiarity_claims(body)
    if mode == "hr_pitch":
        body = _fix_bullet_formatting(body)

    # Appended deterministically, never LLM-generated -- a URL is exactly
    # the kind of token a model can subtly mangle, and this is the one
    # piece of "which specific job" info a recruiter juggling many open
    # roles actually needs to act on the email. The raw internal job_id
    # (an opaque hash) isn't meaningful to them; the real posting link is.
    if apply_url:
        body = f"{body}\n\nJob posting: {apply_url}"

    full_name = f"{profile_manager.get_field('first_name') or ''} {profile_manager.get_field('last_name') or ''}".strip()
    if full_name and full_name not in body:
        body = f"{body}\n\n{full_name}"

    return subject, body, mode
