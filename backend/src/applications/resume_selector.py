import os
from pathlib import Path
from typing import Dict, Any, Tuple

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

    def get_resume(self, job: Dict[str, Any]) -> Tuple[str, str]:
        """
        Returns (resume_path, resume_variant)
        In the future, this will call Resume Tailoring Engine.
        For now, it falls back to the deterministic base resumes.
        """
        role_family = self._determine_role_family(job)
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
