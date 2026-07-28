"""
Persistent Job Description Intelligence Storage & VM Cache Repository.

Stores parsed StructuredJobProfile objects on the VM filesystem.
Deduplicates identical JDs by job_hash and reloads instantly with 0 re-parsing latency.
"""

import os
import json
import logging
from typing import Optional, Dict
from src.resume_intelligence.job_intelligence.models import StructuredJobProfile

logger = logging.getLogger("JobIntelligenceRepository")


class PersistentJobIntelligenceRepository:
    """VM Storage & Instant Cache for Structured Job Profiles."""

    def __init__(self, vm_storage_dir: str = "artifacts/stored_job_intelligence"):
        self.storage_dir = vm_storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self._memory_cache: Dict[str, StructuredJobProfile] = {}

    def get_structured_job(self, job_id: str) -> Optional[StructuredJobProfile]:
        """Loads structured job profile from RAM memory cache or VM JSON disk store."""
        if job_id in self._memory_cache:
            return self._memory_cache[job_id]

        file_path = os.path.join(self.storage_dir, f"{job_id}.json")
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            profile = StructuredJobProfile(**data)
            self._memory_cache[job_id] = profile
            return profile
        except Exception as e:
            logger.error("Failed to load structured job profile %s: %s", job_id, e)
            return None

    def save_structured_job(self, profile: StructuredJobProfile) -> str:
        """Persists structured job profile to VM filesystem JSON store."""
        file_path = os.path.join(self.storage_dir, f"{profile.job_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=2)

        self._memory_cache[profile.job_id] = profile
        logger.info("Persisted StructuredJobProfile %s to VM disk store: %s", profile.job_id, file_path)
        return file_path
