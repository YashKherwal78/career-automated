"""
Semantic Diff Reporter — per-bullet diff after all rewrites are finalized.

Produces SemanticDiffEntry for every bullet, capturing:
  - action verb change (old → new)
  - keywords added from JD
  - whether Google XYZ impact language is used
  - whether ownership level changed
  - whether the original was kept due to low confidence

This makes debugging and auditing much easier than raw text comparison.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.resume_intelligence.tailoring.jake_tex_parser import ParsedResumeTree
from src.resume_intelligence.tailoring.models_v1 import SemanticDiffEntry


# ---------------------------------------------------------------------------
# Verb taxonomy (ownership level detection)
# ---------------------------------------------------------------------------

_LEAD_VERBS = frozenset({
    "led", "spearheaded", "founded", "architected", "directed",
    "established", "pioneered", "championed", "oversaw", "defined",
})

_OWNER_VERBS = frozenset({
    "built", "developed", "engineered", "designed", "shipped", "launched",
    "created", "implemented", "deployed", "owned", "delivered", "executed",
    "formulated", "orchestrated", "constructed",
})

_CONTRIBUTOR_VERBS = frozenset({
    "contributed", "collaborated", "supported", "assisted", "helped",
    "maintained", "participated", "worked", "joined",
})


def _classify_verb(verb: str) -> str:
    """Return LEAD / OWNER / CONTRIBUTOR / UNKNOWN."""
    v = verb.lower().rstrip(".,;")
    if v in _LEAD_VERBS:
        return "LEAD"
    if v in _OWNER_VERBS:
        return "OWNER"
    if v in _CONTRIBUTOR_VERBS:
        return "CONTRIBUTOR"
    return "UNKNOWN"


def _first_word(text: str) -> str:
    """Extract the first word from text, stripping punctuation."""
    words = text.strip().split()
    return words[0].rstrip(".,;:") if words else ""


# XYZ impact language markers
_XYZ_IMPACT_MARKERS = [
    "resulting in", "reducing", "increasing", "improving",
    "enabling", "saving", "growing", "achieving", "delivering",
    "cutting", "boosting", "eliminating", "accelerating",
]

# Metric pattern for detecting quantified impact
_METRIC_RE = re.compile(r"\d+(?:[.,]\d+)*\s*(?:%|x|ms|s|K|M|B|\+)?")


class SemanticDiffReporter:
    """
    Generates the diff log after all rewrites + macro restoration are complete.
    Operates on finalized strings (macros restored, placeholders gone).
    """

    def __init__(self, jd_profile: Dict[str, Any]):
        ats_keywords = jd_profile.get("ats_keywords", [])
        self._jd_keywords = frozenset(
            k.get("normalized_keyword", k.get("keyword", "")).lower()
            for k in ats_keywords
        )
        priority = jd_profile.get("strategy_signals", {}).get("priority_keywords", [])
        self._priority_keywords = frozenset(k.lower() for k in priority)
        self._all_keywords = self._jd_keywords | self._priority_keywords

    def generate(
        self,
        tree: ParsedResumeTree,
        patched_bullets: Dict[str, List[List[str]]],
        kept_originals: Dict[str, List[List[bool]]],
        confidences: Dict[str, List[List[float]]],
    ) -> List[SemanticDiffEntry]:
        """
        Args:
            tree: Original ParsedResumeTree (before patching).
            patched_bullets: {section_name → [[bullet_text per bullet] per entry]}
            kept_originals: {section_name → [[bool per bullet] per entry]}
            confidences: {section_name → [[float per bullet] per entry]}

        Returns:
            List[SemanticDiffEntry] — one entry per bullet across all sections.
        """
        entries: List[SemanticDiffEntry] = []

        for sec in tree.sections:
            section_name = sec.name
            patched_section = patched_bullets.get(section_name, [])
            kept_section = kept_originals.get(section_name, [])
            conf_section = confidences.get(section_name, [])

            for ei, parsed_entry in enumerate(sec.entries):
                heading = (
                    parsed_entry.heading_tokens[0]
                    if parsed_entry.heading_tokens
                    else f"Entry {ei}"
                )
                patched_entry = patched_section[ei] if ei < len(patched_section) else []
                kept_entry = kept_section[ei] if ei < len(kept_section) else []
                conf_entry = conf_section[ei] if ei < len(conf_section) else []

                for bi, parsed_bullet in enumerate(parsed_entry.bullets):
                    original = parsed_bullet.raw_content
                    rewritten = (
                        patched_entry[bi] if bi < len(patched_entry) else original
                    )
                    kept = kept_entry[bi] if bi < len(kept_entry) else False
                    confidence = conf_entry[bi] if bi < len(conf_entry) else 1.0

                    diff = self._diff_bullet(
                        section=section_name,
                        heading=heading,
                        bullet_index=bi,
                        original=original,
                        rewritten=rewritten,
                        kept_original=kept,
                        confidence=confidence,
                    )
                    entries.append(diff)

        return entries

    def _diff_bullet(
        self,
        section: str,
        heading: str,
        bullet_index: int,
        original: str,
        rewritten: str,
        kept_original: bool,
        confidence: float,
    ) -> SemanticDiffEntry:
        old_verb = _first_word(original)
        new_verb = _first_word(rewritten)
        old_level = _classify_verb(old_verb)
        new_level = _classify_verb(new_verb)

        # Keywords added: present in rewritten but not original
        orig_lower = original.lower()
        rew_lower = rewritten.lower()
        keywords_added = [
            kw for kw in self._all_keywords
            if kw in rew_lower and kw not in orig_lower
        ]

        # XYZ impact language detection
        xyz_used = any(m in rew_lower for m in _XYZ_IMPACT_MARKERS)

        # Ownership preserved: level didn't change or improved
        ownership_preserved = (
            old_level == new_level
            or old_level == "UNKNOWN"
            or new_level == "UNKNOWN"
            or (old_level == "CONTRIBUTOR" and new_level in ("OWNER", "LEAD"))
        )
        if old_level in ("LEAD", "OWNER") and new_level == "CONTRIBUTOR":
            ownership_preserved = False

        # Rules applied tracking
        rules_applied: List[str] = []
        if old_verb.lower() != new_verb.lower():
            rules_applied.append("strong_action_verb")
        if xyz_used:
            rules_applied.append("google_xyz")
        if keywords_added:
            rules_applied.append("ats_keyword_injection")
        if ownership_preserved:
            rules_applied.append("ownership_preservation")

        return SemanticDiffEntry(
            section=section,
            company_or_project=heading,
            bullet_index=bullet_index,
            original=original,
            rewritten=rewritten,
            keywords_added=keywords_added,
            action_verb={"old": old_verb, "new": new_verb},
            xyz_used=xyz_used,
            ownership_preserved=ownership_preserved,
            confidence=confidence,
            kept_original=kept_original,
            evidence_sources=[f"base_resume.{section.lower()}[{heading}].bullet[{bullet_index}]"],
            jd_keywords_targeted=list(self._all_keywords)[:5],
            rules_applied=rules_applied,
        )
