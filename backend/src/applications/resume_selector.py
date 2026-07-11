import os
from typing import Dict, Any, Tuple

class ResumeSelector:
    def __init__(self, data_dir: str = "data"):
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
            raise Exception(f"Resume file not found: {resume_path}")
            
        return resume_path, role_family
