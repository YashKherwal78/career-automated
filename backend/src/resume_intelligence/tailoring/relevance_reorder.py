"""
Relevance-based bullet reordering — the core new capability motivated by the
actual evidence on how resumes get read (see project research notes):
recruiters spend ~7 seconds per resume and visual attention concentrates on
the first bullets under each role. Rewriting bullet *wording* in place
(what engine_v1 already did) is the smaller lever; *which bullet leads*
is the bigger one.

This module re-uses resume_knowledge/rules/bullet_scoring.yaml's formula,
but — unlike base_resume/bullet_scoring.py, which has no JD to compare
against — fills in the JD-relative terms the formula actually specifies
(required_skill_match, technology_match, demonstrated_competency_match,
industry_value_match), since tailoring always has a real StructuredJobProfile
to score against.

No LLM calls. Reordering only ever permutes existing (already fact-checked,
already-written) bullet text between slots within the same entry — it never
adds, removes, or rewrites content, so it cannot violate IntegrityGate's
bullet/section count locks.
"""

from __future__ import annotations

import re
from typing import Any, Dict

from src.resume_intelligence.base_resume.bullet_scoring import score_bullet as _score_bullet_base

REQUIRED_SKILL_MATCH = 5
DEMONSTRATED_COMPETENCY_MATCH = 3
TECHNOLOGY_MATCH = 2
INDUSTRY_VALUE_MATCH = 2

_WORD_RE = re.compile(r"[a-zA-Z]{4,}")


def score_bullet_relevance(text: str, jd_profile: Dict[str, Any]) -> float:
    """
    Higher is better. Combines the JD-independent quality signals (metric
    presence, vague wording, passive voice — from base_resume's formula)
    with JD-relative relevance (does this bullet actually speak to what
    this specific job asks for).
    """
    if not text:
        return -999.0

    score = _score_bullet_base(text)
    lowered = text.lower()

    for skill in jd_profile.get("required_skills") or []:
        name = skill.get("normalized_name") or skill.get("name") if isinstance(skill, dict) else str(skill)
        if name and name.lower() in lowered:
            score += REQUIRED_SKILL_MATCH

    for tech in jd_profile.get("technologies") or []:
        if isinstance(tech, str) and tech.lower() in lowered:
            score += TECHNOLOGY_MATCH

    # Responsibilities are free-text, not keywords — a crude content-word
    # overlap is the deterministic (no-LLM) proxy for "this bullet
    # demonstrates a responsibility the JD actually asks for". Counted once
    # per bullet, not once per responsibility, so a bullet can't rack up
    # points just by overlapping with many similar-sounding lines.
    for resp in jd_profile.get("responsibilities") or []:
        resp_words = _WORD_RE.findall(resp.lower()) if isinstance(resp, str) else []
        if resp_words and any(w in lowered for w in resp_words):
            score += DEMONSTRATED_COMPETENCY_MATCH
            break

    strategy_signals = jd_profile.get("strategy_signals") or {}
    for kw in strategy_signals.get("priority_keywords") or []:
        if isinstance(kw, str) and kw.lower() in lowered:
            score += INDUSTRY_VALUE_MATCH

    return score


def compute_reorder_permutation(
    final_texts: Dict[tuple, str],
    entry_count: int,
    jd_profile: Dict[str, Any],
) -> Dict[tuple, tuple]:
    """
    Computes {new_slot: source_slot} across all entries in a section, where
    new_slot and source_slot are both (entry_idx, bullet_idx) keys into the
    same dicts engine_v1 already carries (final text, kept-original flag,
    confidence). Reordering is scoped per entry — bullets never move
    between different jobs/projects, only within the same one.

    Callers apply this ONE permutation to every parallel per-bullet dict
    (final text, kept flag, confidence) so a bullet's provenance travels
    with it to its new slot instead of a slot silently describing a
    different bullet than the one now sitting in it.
    """
    permutation: Dict[tuple, tuple] = {}
    for entry_idx in range(entry_count):
        entry_slots = sorted(
            bullet_idx for (ei, bullet_idx) in final_texts if ei == entry_idx
        )
        if not entry_slots:
            continue
        ranked = sorted(
            entry_slots,
            key=lambda bi: (
                -score_bullet_relevance(final_texts[(entry_idx, bi)], jd_profile),
                bi,
            ),
        )
        for new_bi, source_bi in zip(entry_slots, ranked):
            permutation[(entry_idx, new_bi)] = (entry_idx, source_bi)
    return permutation


def apply_permutation(permutation: Dict[tuple, tuple], values: Dict[tuple, Any]) -> Dict[tuple, Any]:
    """Reassigns `values` (keyed by the same (entry_idx, bullet_idx) slots) per `permutation`."""
    return {new_slot: values[source_slot] for new_slot, source_slot in permutation.items() if source_slot in values}
