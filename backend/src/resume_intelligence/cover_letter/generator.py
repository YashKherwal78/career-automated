"""
Cover Letter Generator V2.

Two-step pipeline, not one:
  1. Role-intent analysis: what is this employer actually hiring for (not
     just which keywords appear in the JD), and which of the candidate's
     real facts are actually relevant evidence for that -- ranked, not just
     selected.
  2. Letter writing: Problem-Solution format (see models.py for the
     research backing that choice), built from the top-ranked facts, not
     the full fact list.

V1 gave the writing call every resume_fact and one instruction ("pick the
2-4 most relevant") -- in practice this let the model gravitate toward
whichever facts sounded most technically impressive (distributed systems,
concurrency, infra) regardless of whether the role was hiring for that at
all. An "AI Product Enablement" JD doesn't need the parser/protocol-parsing
story; it needs the AI-experimentation/workflow-validation one, even though
the former sounds more technically deep. Separating "what does this role
need" from "which facts prove I have it" into its own step, before writing
starts, is what actually fixes that -- an instruction embedded in the
writing prompt competes with the model's own sense of what sounds
impressive and loses often enough to be a real, repeatable problem.

No buzzwords, no "I am writing to apply for" openers, no invented facts —
every claim must trace back to resume_facts or jd_profile, the same
grounding discipline the tailoring engine already enforces.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

from src.config.config import Config
from src.resume_intelligence.cover_letter.models import (
    CoverLetterInput,
    CoverLetterResult,
    RankedFact,
    RoleIntent,
)
from src.resume_intelligence.cover_letter.pdf_renderer import render_cover_letter_tex

logger = logging.getLogger("CoverLetterGenerator")

# Prompt instructions alone don't reliably keep the model off generic
# corporate filler (confirmed here the same way it was confirmed for
# src/referrals/hr_referral_pitch.py's outreach emails: repeated live
# generations still produced "leveraged" etc. despite an explicit ban) —
# swap in a plainer synonym instead of deleting, since these words usually
# sit inside an otherwise fine, information-bearing sentence in a letter
# this short, where dropping the word would leave a grammar gap.
_BUZZWORD_REPLACEMENTS = {
    r"\bleveraging\b": "using",
    r"\bleveraged\b": "used",
    r"\bleverage\b": "use",
}

_BUZZWORD_RE = [
    (re.compile(pattern, re.IGNORECASE), repl)
    for pattern, repl in _BUZZWORD_REPLACEMENTS.items()
]


_MARKDOWN_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_markdown_json_fence(text: str) -> str:
    """Groq (response_format=json_object) and Gemini (response_mime_type=
    application/json) both structurally guarantee bare JSON. OpenRouter has
    no equivalent enforcement across arbitrary underlying models, and
    confirmed live (2026-08-23) it wraps output in a ```json ... ``` fence
    even when told to return JSON only -- json.loads() on that raw string
    raises. Only ever unwraps a fence that spans the WHOLE string, so real
    JSON content that happens to contain a code-fence-like substring inside
    a field value is left untouched."""
    match = _MARKDOWN_JSON_FENCE_RE.match(text.strip())
    return match.group(1).strip() if match else text


def _strip_buzzwords(text: str) -> str:
    for pattern, repl in _BUZZWORD_RE:
        text = pattern.sub(repl, text)
    return text


def _normalize_whitespace(text: str) -> str:
    """The model sometimes emits the JSON string value with embedded
    newlines and leading spaces per line (looks fine in the raw JSON,
    renders as broken ragged indentation once displayed as a letter) --
    collapse each paragraph back to a single line, keep real paragraph
    breaks (blank lines) as-is."""
    paragraphs = [p.strip() for p in text.split("\n\n")]
    cleaned = []
    for para in paragraphs:
        # A paragraph that itself contains single newlines (the broken
        # case) gets its lines joined with spaces; a paragraph that was
        # already one line is unaffected.
        joined = " ".join(line.strip() for line in para.splitlines() if line.strip())
        if joined:
            cleaned.append(joined)
    return "\n\n".join(cleaned)


# Same fallback chain LLMRouter (src/utils/llm_router.py) uses for Groq --
# kept as a literal copy rather than an import for the same reason this
# whole class is a separate copy (see docstring below). A single
# hardcoded model with no fallback is exactly how this generator went
# down in production: llama-3.3-70b-versatile got deprecated by Groq
# (404), and separately, whichever model IS current can still hit Groq's
# free-tier daily token cap mid-session (429) -- confirmed both, live,
# the same night. Falling through this list turns either into "slightly
# slower" instead of "cover letter generation is down".
_FALLBACK_MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "groq/compound-mini"]


class _LLMCaller:
    """Same provider-agnostic Groq/OpenAI adapter pattern as the tailoring
    engine's LLMCaller — kept as a separate small copy rather than a shared
    import so the cover letter module has no dependency on tailoring
    internals (they're conceptually unrelated documents)."""

    def __init__(self, provider: str, model: str):
        self.provider = provider.lower()
        self.model = model
        self._client = self._init_client()

    def _init_client(self) -> Any:
        if self.provider == "groq":
            try:
                from groq import Groq
                api_key = os.environ.get("GROQ_API_KEY", "")
                return Groq(api_key=api_key) if api_key else None
            except ImportError:
                logger.warning("groq package not installed")
                return None
        return None

    def _init_openrouter_client(self) -> Any:
        """Third-tier fallback, same reasoning as _init_gemini_client above --
        Groq's shared free-tier quota and Gemini's (much smaller) free-tier
        quota can BOTH be exhausted at the same time by other features
        sharing the same keys (confirmed live, 2026-08-23: Groq at
        199935/200000 daily tokens, Gemini capped at just 20-500/day
        depending on model). OpenRouter uses the OpenAI SDK against a
        different base_url, same client library already imported below for
        the (unused-here) "openai" provider branch."""
        try:
            import openai
            api_key = os.environ.get("OPENROUTER_API_KEY") or getattr(Config, "OPENROUTER_API_KEY", "")
            return openai.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key) if api_key else None
        except ImportError:
            logger.warning("openai package not installed (needed for OpenRouter)")
            return None

    def _init_gemini_client(self) -> Any:
        """Lazily built cross-provider fallback client -- only needed once
        every Groq model in _FALLBACK_MODELS has failed. Same client/config
        pattern as LLMRouter._call_gemini (src/utils/llm_router.py), kept as
        a small copy for the same reason the rest of this class is: no
        dependency on tailoring/router internals for a conceptually
        unrelated document type."""
        try:
            from google import genai
            api_key = os.environ.get("GEMINI_API_KEY") or getattr(Config, "GEMINI_API_KEY", "")
            return genai.Client(api_key=api_key) if api_key else None
        except ImportError:
            logger.warning("google-genai package not installed")
            return None

    def call(self, system_prompt: str, user_prompt: str, max_tokens: int = 700) -> Optional[str]:
        if self._client is None:
            logger.warning("CoverLetterGenerator: LLM client unavailable for provider '%s'", self.provider)
            return None

        # Requested model first, then the fallback chain (skipping the
        # requested model if it's already in there, so a caller who passed
        # a non-default model still gets the same resilience).
        models_to_try = [self.model] + [m for m in _FALLBACK_MODELS if m != self.model]

        last_exc: Optional[Exception] = None
        for model in models_to_try:
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content or None
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "CoverLetterGenerator LLM error (%s/%s), trying next fallback: %s",
                    self.provider, model, exc,
                )

        # Every Groq model failed -- confirmed live (2026-08-23): Groq's
        # shared free-tier daily token cap gets exhausted by OTHER features
        # sharing the same org/key (tailoring, extraction, outreach), which
        # took cover letters down with a 503 even though a working,
        # already-configured Gemini client exists elsewhere in this codebase
        # (LLMRouter) -- this class just never fell through to it. Lazily
        # initialize Gemini only now, since the common case (Groq succeeds)
        # shouldn't pay for a client it never uses.
        gemini_client = self._init_gemini_client()
        if gemini_client is not None:
            prompt = f"{system_prompt}\n\n{user_prompt}"
            for model_name in ("gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash"):
                try:
                    from google.genai import types as genai_types
                    response = gemini_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=0.4,
                            response_mime_type="application/json",
                        ),
                    )
                    if response.text:
                        return response.text
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "CoverLetterGenerator LLM error (gemini/%s), trying next fallback: %s",
                        model_name, exc,
                    )

        # Every Gemini model failed too. OpenRouter as a third tier --
        # confirmed live (2026-08-23) that Groq and Gemini's free tiers can
        # BOTH be exhausted simultaneously, so a two-provider fallback still
        # wasn't enough headroom in practice.
        openrouter_client = self._init_openrouter_client()
        if openrouter_client is not None:
            for model_name in ("deepseek/deepseek-chat", "qwen/qwen-2.5-72b-instruct", "meta-llama/llama-3-70b-instruct"):
                try:
                    response = openrouter_client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=0.4,
                        max_tokens=max_tokens,
                    )
                    content = response.choices[0].message.content
                    if content:
                        return _strip_markdown_json_fence(content)
                except Exception as exc:
                    last_exc = exc
                    logger.warning(
                        "CoverLetterGenerator LLM error (openrouter/%s), trying next fallback: %s",
                        model_name, exc,
                    )

        if last_exc:
            logger.error("CoverLetterGenerator: all models exhausted (groq + gemini + openrouter): %s", last_exc)
        return None


# Reference categories, not an exhaustive enum -- the model should name the
# closest fit or something more specific if the JD genuinely doesn't match
# any of these, not force-fit into the nearest bucket.
_ROLE_CATEGORIES = [
    "AI Engineering", "AI Product", "AI Product Enablement", "AI Adoption",
    "Product Management", "Software Engineering", "Data/Analytics",
    "Consulting", "Strategy", "Operations",
]

_ROLE_INTENT_SYSTEM_PROMPT = """You analyze a job description to determine what the employer is actually \
hiring this person to DO -- not which keywords appear in the text -- and then rank a candidate's real, \
factual achievements by how well each one demonstrates that.

Step 1 -- Role intent. Determine:
- role_category: the closest single fit, e.g. one of ({categories}) or a more specific label if none fit. \
Distinguish carefully -- "AI Product Enablement" (helping others adopt/use AI tools, workflow validation, \
documentation, experimentation) is NOT the same as "AI Engineering" (building AI systems) even though both \
JDs will mention similar AI vocabulary.
- primary_function: one sentence, what this person spends most of their time doing in this role.
- top_competencies: the 3-5 capabilities that actually matter most for succeeding in this specific role, \
most important first. Not a copy of the JD's skills list -- your judgment of what actually matters.

Step 2 -- Evidence ranking. You will be given a NUMBERED list of the candidate's real facts (achievements, \
projects, experience). For EACH fact, score 0-10 how strong a piece of evidence it is for THIS role's actual \
needs (role_category/primary_function/top_competencies from step 1) -- not how technically impressive the \
fact is in isolation. A simpler fact that's exactly what the role needs should score higher than an \
impressive fact that's tangential. Give a short (under 12 words) "why" for each score.

Return ONLY valid JSON, no markdown. Reference facts by their number, do NOT copy the fact text itself \
(you'll run out of output space repeating long facts verbatim -- the index is enough, the caller already has \
the text):
{{
  "role_category": "...",
  "primary_function": "...",
  "top_competencies": ["...", "...", "..."],
  "ranked_facts": [
    {{"index": 0, "relevance_score": 0-10, "why": "..."}}
  ]
}}
Every fact number given to you must appear exactly once in ranked_facts.
"""

_ROLE_INTENT_USER_TEMPLATE = """Company: {company_name}
Role: {role_title}

Job description signals:
{jd_summary}

Candidate's real facts to score (reference each by its number, 0-indexed):
{resume_facts}
"""


_SYSTEM_PROMPT = """You write concise, specific cover letters using the Problem-Solution format, built \
around what this role is ACTUALLY hiring for -- not around whichever piece of evidence sounds most \
technically impressive.

You are given: the role's actual intent (what this employer needs), and the candidate's evidence \
pre-ranked by relevance to that intent. Use the evidence roughly in the order given (highest relevance \
first) -- it has already been selected for you as the strongest, most relevant proof, not the most \
technically complex.

Structure (strict):
1. Opening (1-2 sentences): connect the candidate's background directly to what THIS role needs (role_intent), \
not a generic statement about the company or a restatement of the job title. Never open with "I am writing \
to apply for" or "I am excited about this opportunity."
2. Body (2-3 short paragraphs, using the 2-3 ranked evidence facts given): for each piece of evidence, make \
clear WHY it demonstrates something this specific role needs -- don't just state the achievement, connect it \
to the role's actual need. This should read as one coherent narrative connecting the candidate's real \
background to this role's real needs, not a list of separate accomplishments. Use only the facts provided — \
never invent metrics, employers, outcomes, technologies, or years of experience not present in the given \
facts or jd_profile.
3. Close (1 sentence): express interest in the role and invite a conversation about FIT for the role -- not a \
technical deep-dive into whichever specific system was mentioned, unless that system's design is itself \
central to what this role does day to day. Vary the exact wording; don't reuse a fixed template phrase.

Hard rules:
- Write in FIRST PERSON, as the candidate speaking for themselves ("I built...", "I'm ready to..."). NEVER \
third person ("Yash built...", "He is ready..." — the candidate is not being described by someone else, they \
are writing this letter).
- Between {min_words} and {max_words} words total.
- No buzzwords or filler transitions: passionate, excited, great fit, cutting-edge, dynamic, synergy, team \
player, leverage, meaningful impact, drive impact, look forward to discussing. These phrases are generic \
enough to paste into any letter for any job — if a sentence would still make sense with the company and role \
swapped out, rewrite it to be specific to this one instead.
- Do not just restate the job description's own phrasing back with the candidate's name attached -- the \
reader should come away thinking "this person's real experience happens to fit," not "this was keyword-matched."
- Every factual claim must trace to the given facts or jd_profile — if you're not given a fact, don't state it. \
If the role wants something the candidate doesn't have direct evidence for, either omit it or connect it to a \
real, truthful transferable capability — never invent the missing experience.
- Tone: {tone}.
- Return ONLY valid JSON: {{"cover_letter": "..."}}. No markdown, no explanation.
"""

_USER_PROMPT_TEMPLATE = """Company: {company_name}
Role: {role_title}

Job description signals (what this employer actually needs):
{jd_summary}

What this role is actually hiring for (from the role-intent analysis):
- Category: {role_category}
- Primary function: {primary_function}
- What matters most: {top_competencies}

Candidate: {candidate_name}
Evidence to use, in order of relevance to what this role actually needs (use only these — do not invent others):
{resume_facts}

Write the cover letter now, following the Problem-Solution structure and all hard rules.
"""


def _summarize_jd(jd_profile: dict) -> str:
    parts = []
    signals = jd_profile.get("strategy_signals") or {}
    if signals.get("role_type"):
        parts.append(f"Role type: {signals['role_type']}")
    if signals.get("primary_domain"):
        parts.append(f"Domain: {signals['primary_domain']}")
    if signals.get("bullet_strategy"):
        parts.append(f"What they care about: {signals['bullet_strategy']}")
    responsibilities = jd_profile.get("responsibilities") or []
    if responsibilities:
        parts.append("Key responsibilities: " + "; ".join(responsibilities[:4]))
    required = jd_profile.get("required_skills") or []
    if required:
        names = [s.get("normalized_name", s) if isinstance(s, dict) else s for s in required[:8]]
        parts.append("Required skills: " + ", ".join(str(n) for n in names))
    return "\n".join(parts) if parts else "(no structured JD signals available — write generically for the role title)"


def _extract_role_intent_and_rank_facts(
    caller: _LLMCaller,
    jd_profile: dict,
    resume_facts: list[str],
    company_name: str,
    role_title: str,
) -> tuple[Optional[RoleIntent], list[RankedFact]]:
    """Returns (None, []) on any failure -- caller falls back to using
    resume_facts in given order, same behavior as before this step existed,
    rather than blocking letter generation on this step succeeding."""
    system_prompt = _ROLE_INTENT_SYSTEM_PROMPT.format(categories=", ".join(_ROLE_CATEGORIES))
    user_prompt = _ROLE_INTENT_USER_TEMPLATE.format(
        company_name=company_name,
        role_title=role_title,
        jd_summary=_summarize_jd(jd_profile),
        resume_facts="\n".join(f"{i}. {f}" for i, f in enumerate(resume_facts)),
    )
    # Index-based output (see prompt) instead of echoing fact text back
    # verbatim -- with 20+ facts, asking the model to reproduce each one's
    # full text in ranked_facts routinely blew the token budget mid-object
    # and came back truncated/unparseable (confirmed live). Scale the
    # budget with fact count regardless, since "why" text still adds up.
    max_tokens = min(2000, 400 + 60 * len(resume_facts))
    raw = caller.call(system_prompt, user_prompt, max_tokens=max_tokens)
    if not raw:
        return None, []
    try:
        parsed = json.loads(raw)
        intent = RoleIntent(
            role_category=parsed.get("role_category", ""),
            primary_function=parsed.get("primary_function", ""),
            top_competencies=parsed.get("top_competencies") or [],
        )
        ranked = []
        for item in (parsed.get("ranked_facts") or []):
            idx = item.get("index")
            if not isinstance(idx, int) or not (0 <= idx < len(resume_facts)):
                continue
            ranked.append(RankedFact(
                fact=resume_facts[idx],
                relevance_score=float(item.get("relevance_score", 0) or 0),
                why=item.get("why", ""),
            ))
        if not ranked:
            return None, []
        return intent, ranked
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as e:
        logger.warning("CoverLetterGenerator: role-intent step returned unusable output (%s), falling back.", e)
        return None, []


class CoverLetterGenerator:
    def generate(self, inp: CoverLetterInput) -> CoverLetterResult:
        if not inp.resume_facts:
            logger.warning("CoverLetterGenerator: no resume_facts provided — refusing to invent achievements.")
            return CoverLetterResult(
                cover_letter_text="",
                word_count=0,
                llm_calls_made=0,
                is_fallback=True,
            )

        caller = _LLMCaller(inp.llm_provider, inp.llm_model)
        llm_calls_made = 0

        # Step 1: role intent + evidence ranking. Falls back to the given
        # fact order (unranked) on any failure -- this step improves
        # selection quality, it isn't a hard dependency for generating a
        # grounded letter at all.
        role_intent, ranked_facts = _extract_role_intent_and_rank_facts(
            caller, inp.jd_profile, inp.resume_facts, inp.company_name, inp.role_title,
        )
        llm_calls_made += 1

        if ranked_facts:
            ranked_facts_sorted = sorted(ranked_facts, key=lambda r: r.relevance_score, reverse=True)
            top_facts = [r.fact for r in ranked_facts_sorted[:3]]
        else:
            top_facts = inp.resume_facts[:4]
            ranked_facts_sorted = []

        # Step 2: write the letter from the top-ranked (or fallback) facts.
        system_prompt = _SYSTEM_PROMPT.format(min_words=inp.min_words, max_words=inp.max_words, tone=inp.writing_tone)
        user_prompt = _USER_PROMPT_TEMPLATE.format(
            company_name=inp.company_name,
            role_title=inp.role_title,
            jd_summary=_summarize_jd(inp.jd_profile),
            role_category=role_intent.role_category if role_intent else "(not determined — write generically for the role title)",
            primary_function=role_intent.primary_function if role_intent else "",
            top_competencies=", ".join(role_intent.top_competencies) if role_intent else "",
            candidate_name=inp.candidate_name,
            resume_facts="\n".join(f"- {f}" for f in top_facts),
        )

        raw = caller.call(system_prompt, user_prompt)
        llm_calls_made += 1

        if not raw:
            return CoverLetterResult(
                cover_letter_text="",
                word_count=0,
                llm_calls_made=llm_calls_made,
                is_fallback=True,
                role_intent=role_intent,
                ranked_facts=ranked_facts_sorted,
            )

        try:
            parsed = json.loads(raw)
            text = (parsed.get("cover_letter") or "").strip()
        except (json.JSONDecodeError, AttributeError):
            logger.error("CoverLetterGenerator: LLM returned non-JSON response, discarding.")
            text = ""

        if not text:
            return CoverLetterResult(
                cover_letter_text="",
                word_count=0,
                llm_calls_made=llm_calls_made,
                is_fallback=True,
                role_intent=role_intent,
                ranked_facts=ranked_facts_sorted,
            )

        text = _normalize_whitespace(text)
        text = _strip_buzzwords(text)

        word_count = len(text.split())

        # PDF/LaTeX generation must never take down letter generation --
        # the .tex is a presentation concern layered on top of an already-
        # successful letter, so any failure here still returns the real
        # text/word_count, just with cover_letter_tex empty (frontend
        # falls back to text-only download/copy, same as before this
        # feature existed).
        tex = ""
        try:
            tex = render_cover_letter_tex(
                cover_letter_text=text,
                candidate_name=inp.candidate_name,
                candidate_email=inp.candidate_email,
                candidate_phone=inp.candidate_phone,
                company_name=inp.company_name,
                role_title=inp.role_title,
            )
        except Exception as e:
            logger.warning("CoverLetterGenerator: .tex rendering failed (%s) -- text/copy outputs unaffected.", e)

        return CoverLetterResult(
            cover_letter_text=text,
            cover_letter_tex=tex,
            word_count=word_count,
            llm_calls_made=llm_calls_made,
            is_fallback=False,
            role_intent=role_intent,
            ranked_facts=ranked_facts_sorted,
        )
