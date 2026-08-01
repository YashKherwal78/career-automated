"""
CareerMemoryStore — Phase 3 Memory Store Module

Provides persistent long-term longitudinal career profile memory.

Invariant: Zero score mutations.
"""

import json
import os
import logging
from typing import Dict, List, Optional

from src.career_intelligence.memory.models import (
    LongitudinalMemory,
    PreferenceProfile,
)

logger = logging.getLogger("CareerMemoryStore")


class CareerMemoryStore:
    """Manages longitudinal candidate career memory with JSON file-backed persistence."""

    def __init__(self, storage_path: str | None = None) -> None:
        self._storage_path = storage_path or os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "career_memory.json")
        self._memory_store: Dict[str, LongitudinalMemory] = {}
        self._load_from_disk()

    def get_or_create_memory(self, candidate_id: str) -> LongitudinalMemory:
        """Fetch or initialize longitudinal memory for a candidate."""
        if candidate_id in self._memory_store:
            return self._memory_store[candidate_id]

        mem = LongitudinalMemory(
            candidate_id=candidate_id,
            completed_milestones=[],
            accepted_jobs=[],
            rejected_jobs=[],
            preferences=PreferenceProfile(),
        )
        self._memory_store[candidate_id] = mem
        self._save_to_disk()
        return mem

    def mark_milestone_completed(self, candidate_id: str, milestone_name: str) -> LongitudinalMemory:
        """Record a completed learning milestone in candidate memory."""
        mem = self.get_or_create_memory(candidate_id)
        if milestone_name not in mem.completed_milestones:
            updated_list = list(mem.completed_milestones) + [milestone_name]
            updated_mem = mem.model_copy(update={"completed_milestones": updated_list})
            self._memory_store[candidate_id] = updated_mem
            self._save_to_disk()
            logger.info("CareerMemoryStore: marked milestone '%s' completed for candidate %s", milestone_name, candidate_id)
            return updated_mem
        return mem

    def add_favorite_company(self, candidate_id: str, company_name: str) -> LongitudinalMemory:
        """Add a company to candidate's favorite list."""
        mem = self.get_or_create_memory(candidate_id)
        favs = list(mem.preferences.favorite_companies)
        if company_name not in favs:
            favs.append(company_name)
            updated_prefs = mem.preferences.model_copy(update={"favorite_companies": favs})
            updated_mem = mem.model_copy(update={"preferences": updated_prefs})
            self._memory_store[candidate_id] = updated_mem
            self._save_to_disk()
            return updated_mem
        return mem

    # ── Persistence Helpers ──

    def _load_from_disk(self) -> None:
        """Load stored memory JSON from disk if file exists."""
        try:
            if os.path.exists(self._storage_path):
                with open(self._storage_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for cand_id, raw_mem in raw_data.items():
                        self._memory_store[cand_id] = LongitudinalMemory.model_validate(raw_mem)
                logger.info("CareerMemoryStore: loaded %d longitudinal profiles from %s", len(self._memory_store), self._storage_path)
        except Exception as e:
            logger.warning("CareerMemoryStore: failed loading from disk (%s), using memory store", e)

    def _save_to_disk(self) -> None:
        """Persist memory JSON to disk."""
        try:
            os.makedirs(os.path.dirname(self._storage_path), exist_ok=True)
            dump_data = {k: v.model_dump() for k, v in self._memory_store.items()}
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=2)
        except Exception as e:
            logger.warning("CareerMemoryStore: failed persisting to disk (%s)", e)
