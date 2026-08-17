"""
Cover letter generator's I/O contract. Deliberately small and separate from
the tailoring engine's models — a cover letter isn't a resume mutation, it's
a fresh short document, so it doesn't need base_tex/macro-masking/integrity-
gate machinery. It does reuse the same jd_profile shape tailoring already
consumes (StructuredJobProfile.model_dump()), so callers don't need to parse
the JD twice.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Research backing this format (see PR/commit message for sources): 94% of
# hiring managers say cover letters influence interview decisions; a weak
# generic one can actively hurt a strong candidate (18% say so). The
# consistently best-performing structure across 80+ studies is
# Problem-Solution: name the employer's specific need first, then position
# the candidate's quantified experience as the fix — not a life story.
DEFAULT_MAX_WORDS = 250


class CoverLetterInput(BaseModel):
    candidate_name: str
    candidate_email: str
    candidate_phone: str = ""

    jd_profile: Dict[str, Any]
    """Same StructuredJobProfile shape the tailoring engine consumes."""

    resume_facts: List[str] = Field(default_factory=list)
    """Short, quantified achievement facts pulled from the candidate's real
    profile/resume — the same kind of "candidate_memory" facts tailoring
    already builds from user_career_profiles, not free-form LLM invention."""

    company_name: str = "Unknown"
    role_title: str = "the role"

    writing_tone: str = "Professional"
    """Reuses the same Settings > AI Preferences value tailoring already
    reads, for a consistent voice across tailored resume + cover letter."""

    max_words: int = DEFAULT_MAX_WORDS
    llm_provider: str = "groq"
    # llama-3.3-70b-versatile was deprecated/removed by Groq (confirmed
    # live: 404 model_not_found) -- matches LLMRouter's current primary
    # candidate (llm_router.py's candidate_models[0]), which this
    # generator doesn't route through (deliberately separate client, see
    # generator.py's docstring) so it never picked up that fix.
    llm_model: str = "openai/gpt-oss-120b"


class CoverLetterResult(BaseModel):
    cover_letter_text: str
    word_count: int
    llm_calls_made: int = 0
    is_fallback: bool = False
    """True if the LLM call failed and this is a safe, honest fallback
    (never a hallucinated placeholder pretending to be a real letter)."""
