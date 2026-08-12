import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from src.system.logger import setup_logger

logger = setup_logger("resume_selector")

# Resolved from this file's own location (backend/src/applications/ -> ../../data
# -> backend/data, /app/data in the container) rather than a bare "data"
# relative to the process's current working directory. A relative default
# works fine as long as every caller happens to run with CWD == the backend
# root, but that's an assumption, not a guarantee -- a plain relative path
# gave zero indication of *which* directory it actually meant when a resume
# genuinely went missing (bind-mount got orphaned by a host-side directory
# recreation -- see the RUNNER_ERROR incident this fixed), it was just
# "data/Yash_product.pdf" with no way to tell if that path was even pointed
# at the right place.
_DEFAULT_DATA_DIR = str(Path(__file__).resolve().parents[2] / "data")


class ResumeSelector:
    def __init__(self, data_dir: str = _DEFAULT_DATA_DIR):
        self.data_dir = data_dir

        # Base resumes map
        self.base_resumes = {
            "Product": "Yash_product.pdf",
            "AI": "Resume_aiml.pdf",
            "SWE": "Resume_aiml.pdf" # Fallback if we don't have a SWE specific one
        }

    def _determine_role_family(self, job: Dict[str, Any]) -> str:
        domain = job.get("jqe_domain", "").lower()
        title = job.get("job_title", "").lower()
        
        if "product" in domain or "product" in title or "apm" in title:
            return "Product"
        elif "ai" in domain or "ai" in title or "machine learning" in title or "ml" in title:
            return "AI"
        elif "software" in domain or "software" in title or "developer" in title or "engineer" in title:
            return "SWE"
        
        # Default fallback
        return "Product"

    def _get_uploaded_resume(self, user_id: str) -> Optional[str]:
        """Downloads (fresh, from R2 -- not the stored presigned URL, which
        expires 7 days after upload) the resume this specific user actually
        uploaded via the dashboard, caching it locally. Returns None if the
        user hasn't uploaded one, in which case the caller falls back to a
        generic default -- but never silently substitutes a DIFFERENT
        person's or a stale placeholder resume for a user who HAS uploaded
        their own (that was the actual bug this replaces: every real
        application went out with a static file from the initial commit,
        unrelated to and predating any real per-user upload)."""
        try:
            from src.api.db import get_connection
            from src.runtime.storage.storage_service import StorageService

            with get_connection() as conn:
                cur = conn.execute(
                    "SELECT file_name FROM public.user_resumes WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
            if not row:
                return None
            file_name = row["file_name"] if hasattr(row, "keys") else row[0]
            if not file_name:
                return None

            cache_dir = os.path.join(self.data_dir, "cache", "resumes")
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, f"{user_id}_{file_name}")

            key = f"resumes/{user_id}/{file_name}"
            if StorageService.download_file(key, cache_path):
                return cache_path

            # Download failed (network hiccup, R2 issue) -- reuse a
            # previously cached copy rather than falling all the way back
            # to the generic default, if one exists from an earlier
            # successful fetch.
            if os.path.exists(cache_path):
                logger.info(f"R2 download failed for {key}, reusing cached copy at {cache_path}")
                return cache_path
            return None
        except Exception as e:
            logger.info(f"Failed to resolve uploaded resume for user_id={user_id}: {e}")
            return None

    def get_resume(self, job: Dict[str, Any], user_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Returns (resume_path, resume_variant). Prefers the specific resume
        this user actually uploaded (see _get_uploaded_resume) when
        user_id is supplied and a real upload exists; falls back to the
        generic role-family default otherwise -- e.g. for a user who
        hasn't uploaded a resume yet, or when user_id isn't known at the
        call site.
        """
        role_family = self._determine_role_family(job)

        if user_id:
            uploaded_path = self._get_uploaded_resume(user_id)
            if uploaded_path:
                return uploaded_path, role_family

        variant_name = self.base_resumes.get(role_family, "Yash_product.pdf")
        resume_path = os.path.join(self.data_dir, variant_name)

        if not os.path.exists(resume_path):
            # Distinguish "this one file is missing" from "the whole data
            # directory is empty/unmounted" -- the latter is an infra
            # problem (e.g. a bind mount pointing at a stale/orphaned
            # directory) that will fail identically for every job in a
            # batch run, not something specific to this resume variant.
            if not os.path.isdir(self.data_dir):
                raise Exception(f"Resume data directory does not exist: {self.data_dir}")
            if not os.listdir(self.data_dir):
                raise Exception(f"Resume data directory is empty (likely an unmounted/stale volume): {self.data_dir}")
            raise Exception(f"Resume file not found: {resume_path}")

        return resume_path, role_family
