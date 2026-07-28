"""
Candidate Memory — typed evidence wrapper.

Wraps the unstructured candidate_memory dict into a typed interface
that the engine uses to pull evidence for bullet context and summary building.

The candidate_memory dict schema (expected by the platform):
  {
    "global": ["fact 1", "fact 2", ...],          # general candidate facts
    "bullet:<section>:<entry>:<index>": ["..."],  # per-bullet evidence
    "project:<title>": ["..."],                    # per-project evidence
    "technology:<name>": ["..."],                  # per-technology evidence
  }
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class CandidateMemory:
    """
    Typed interface over the raw candidate_memory dict.
    All retrieval methods return lists of strings (never raise KeyError).
    """

    def __init__(self, raw: Dict[str, Any]):
        self._raw = raw

    # ── Global evidence ────────────────────────────────────────────────────

    def get_global_facts(self) -> List[str]:
        """All-purpose candidate facts for summary building."""
        val = self._raw.get("global", [])
        return val if isinstance(val, list) else []

    # ── Bullet-level evidence ──────────────────────────────────────────────

    def get_bullet_evidence(
        self,
        section: str,
        entry_index: int,
        bullet_index: int,
    ) -> List[str]:
        """Evidence for a specific bullet at section/entry/bullet indices."""
        key = f"bullet:{section}:{entry_index}:{bullet_index}"
        val = self._raw.get(key, [])
        return val if isinstance(val, list) else []

    # ── Project evidence ───────────────────────────────────────────────────

    def get_project_evidence(self, project_title: str) -> List[str]:
        key = f"project:{project_title}"
        val = self._raw.get(key, [])
        return val if isinstance(val, list) else []

    # ── Technology evidence ────────────────────────────────────────────────

    def get_technology_evidence(self, tech_name: str) -> List[str]:
        key = f"technology:{tech_name}"
        val = self._raw.get(key, [])
        return val if isinstance(val, list) else []

    # ── Helpers ────────────────────────────────────────────────────────────

    def get_all_facts_flat(self, max_facts: int = 12) -> List[str]:
        """
        Returns a flattened, deduplicated list of all evidence strings
        for use when building the summary prompt.
        """
        seen: set = set()
        result: List[str] = []

        for val in self._raw.values():
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item not in seen:
                        seen.add(item)
                        result.append(item)
                        if len(result) >= max_facts:
                            return result

        return result

    def is_empty(self) -> bool:
        return not bool(self._raw)
