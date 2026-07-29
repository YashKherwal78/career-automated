"""
Deterministic bullet quality scoring, per resume_knowledge/rules/bullet_scoring.yaml.

Base-resume generation has no job description to match against, so the JD-relative
terms in that formula (required_skill_match, missing_required_skill_penalty,
industry_value_match) don't apply here — they're used by the tailoring engine at
tailor-time instead. This scores only the JD-independent signals: verified metrics,
vague wording, and passive voice — used purely to decide which bullets survive
page-fit trimming when a section has to be shortened.
"""

from __future__ import annotations

import re

_METRIC_PATTERN = re.compile(r"\d")
_VAGUE_PHRASES = (
    "responsible for",
    "helped with",
    "worked on",
    "involved in",
    "assisted with",
    "in charge of",
    "duties included",
)
_PASSIVE_MARKERS = re.compile(
    r"\b(was|were|been|being|is|are)\s+\w+ed\b", re.IGNORECASE
)

HAS_METRIC = 2
VAGUE_WORDING_PENALTY = -5
PASSIVE_VOICE_PENALTY = -5


def score_bullet(text: str) -> float:
    """Higher is better. Used to rank bullets for trim-order during page-fit."""
    if not text:
        return -999
    score = 0.0
    if _METRIC_PATTERN.search(text):
        score += HAS_METRIC
    lowered = text.lower()
    if any(phrase in lowered for phrase in _VAGUE_PHRASES):
        score += VAGUE_WORDING_PENALTY
    if _PASSIVE_MARKERS.search(text):
        score += PASSIVE_VOICE_PENALTY
    return score


def rank_bullet_indices(bullets: list[str]) -> list[int]:
    """
    Returns bullet indices ordered weakest-first (candidates to drop first),
    per tie_break_order: score ascending, then original order descending
    (drop the latest-added / lowest-priority bullet first on ties).
    """
    scored = [(i, score_bullet(b)) for i, b in enumerate(bullets)]
    scored.sort(key=lambda pair: (pair[1], -pair[0]))
    return [i for i, _ in scored]
