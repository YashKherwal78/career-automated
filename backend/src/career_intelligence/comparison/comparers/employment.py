from typing import Dict, Any
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class EmploymentComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares job employment contract type format against candidate experience profile history."""
        if job.employment_type == "Unknown":
            return {"employment_type_fit": True}
            
        candidate_pref_types = set()
        for exp in profile.experience:
            if exp.employment_type:
                candidate_pref_types.add(exp.employment_type.lower())
                
        fit = len(candidate_pref_types) == 0 or job.employment_type.lower() in candidate_pref_types
        return {
            "employment_type_fit": fit
        }
