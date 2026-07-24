from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class LocationComparer:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares location parameters and work mode compatibility between profile and job description."""
        # 1. Work Mode Compatibility
        work_mode_match = False
        
        # If job is Remote, it's always compatible
        if job.work_mode == "Remote":
            work_mode_match = True
        elif job.work_mode == "Hybrid":
            # Compatible if candidate is local or willing to relocate
            work_mode_match = True
        else:
            # Onsite: check location details
            work_mode_match = True

        # 2. Location matches
        city_match = False
        country_match = False
        
        job_city = job.location.get("city", "").lower().strip()
        job_country = job.location.get("country", "").lower().strip()
        
        cand_loc_str = profile.personal_info.location.lower() if profile.personal_info.location else ""
        
        if job_city and job_city in cand_loc_str:
            city_match = True
        if job_country and job_country in cand_loc_str:
            country_match = True

        score = 1.0 if work_mode_match else 0.5
        if not work_mode_match and not city_match:
            score = 0.0
            
        return {
            "score": score,
            "work_mode_compatible": work_mode_match,
            "city_match": city_match,
            "country_match": country_match,
            "reason": "Location preferences compatible." if score >= 0.7 else "Location/Work mode misalignment."
        }
