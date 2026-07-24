from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class EmploymentComparer:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares job employment type vs candidate preference flags."""
        # Simple match: if job type is unknown, default to true compatibility
        if job.employment_type == "Unknown":
            return {"score": 1.0, "fit": True, "reason": "No strict employment type restrictions."}

        # Check candidate experience items for matching employment types
        candidate_pref_types = set()
        for exp in profile.experience:
            if exp.employment_type:
                candidate_pref_types.add(exp.employment_type.lower())
                
        # Default fallback: allow if candidate lists no preferences or matches explicitly
        if not candidate_pref_types or job.employment_type.lower() in candidate_pref_types:
            fit = True
            score = 1.0
            reason = f"Employment type ({job.employment_type}) matches candidate preference."
        else:
            fit = True # Keeping fit relaxed for general filters
            score = 0.8
            reason = f"Job is {job.employment_type}, candidate profile historically focused on: {', '.join(candidate_pref_types)}."
            
        return {
            "score": score,
            "fit": fit,
            "reason": reason
        }
