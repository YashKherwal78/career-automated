"""
Cover Letter Generator V1.

Problem-Solution format (see models.py for the research backing this
choice): name the employer's specific need from the JD first, then position
the candidate's quantified real experience as the fix. Short (~250 words),
no buzzwords, no "I am writing to apply for" openers, no invented facts —
every claim must trace back to resume_facts or jd_profile, the same
grounding discipline the tailoring engine already enforces.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

from src.resume_intelligence.cover_letter.models import CoverLetterInput, CoverLetterResult

logger = logging.getLogger("CoverLetterGenerator")


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

    def call(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if self._client is None:
            logger.warning("CoverLetterGenerator: LLM client unavailable for provider '%s'", self.provider)
            return None
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=700,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or None
        except Exception as exc:
            logger.error("CoverLetterGenerator LLM error (%s/%s): %s", self.provider, self.model, exc)
            return None


_SYSTEM_PROMPT = """You write short, specific cover letters using the Problem-Solution format.

Structure (strict):
1. Opening (1-2 sentences): name the SPECIFIC need or challenge implied by the job description. Never open with "I am writing to apply for" or "I am excited about this opportunity."
2. Body (2-3 short paragraphs): position the candidate's real, quantified achievements (given to you as resume_facts) as the direct answer to that need. Use only the facts provided — never invent metrics, employers, or outcomes not present in resume_facts or jd_profile.
3. Close (1-2 sentences): confident, specific next step. No desperation ("I would be grateful", "please consider"), no generic enthusiasm ("passionate about", "great fit", "cutting-edge").

Hard rules:
- Write in FIRST PERSON, as the candidate speaking for themselves ("I built...", "I'm ready to..."). NEVER third person ("Yash built...", "He is ready..." — the candidate is not being described by someone else, they are writing this letter).
- Maximum {max_words} words total.
- No buzzwords: passionate, excited, great fit, cutting-edge, dynamic, synergy, team player.
- Every factual claim must trace to resume_facts or jd_profile — if you're not given a fact, don't state it.
- Tone: {tone}.
- Return ONLY valid JSON: {{"cover_letter": "..."}}. No markdown, no explanation.
"""

_USER_PROMPT_TEMPLATE = """Company: {company_name}
Role: {role_title}

Job description signals (what this employer actually needs):
{jd_summary}

Candidate: {candidate_name}
Real, quantified achievements to draw from (use only these — do not invent others):
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
        system_prompt = _SYSTEM_PROMPT.format(max_words=inp.max_words, tone=inp.writing_tone)
        user_prompt = _USER_PROMPT_TEMPLATE.format(
            company_name=inp.company_name,
            role_title=inp.role_title,
            jd_summary=_summarize_jd(inp.jd_profile),
            candidate_name=inp.candidate_name,
            resume_facts="\n".join(f"- {f}" for f in inp.resume_facts),
        )

        raw = caller.call(system_prompt, user_prompt)
        llm_calls_made = 1

        if not raw:
            return CoverLetterResult(
                cover_letter_text="",
                word_count=0,
                llm_calls_made=llm_calls_made,
                is_fallback=True,
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
            )

        word_count = len(text.split())
        return CoverLetterResult(
            cover_letter_text=text,
            word_count=word_count,
            llm_calls_made=llm_calls_made,
            is_fallback=False,
        )
