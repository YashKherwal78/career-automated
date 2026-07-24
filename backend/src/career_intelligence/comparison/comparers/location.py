from typing import Dict, Any
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class LocationComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares location parameters City/State/Country and work mode preferences."""
        job_city = job.location.get("city", "").lower().strip()
        job_country = job.location.get("country", "").lower().strip()
        
        cand_loc_str = profile.personal_info.location.lower() if profile.personal_info.location else ""
        
        city_match = False
        country_match = False
        
        if job_city and job_city in cand_loc_str:
            city_match = True
        if job_country and job_country in cand_loc_str:
            country_match = True

        # Work Mode fit evaluation
        work_mode_fit = False
        if job.work_mode == "Remote":
            work_mode_fit = True
        elif job.work_mode == "Hybrid":
            work_mode_fit = True
        else:
            # Onsite: check location details
            work_mode_fit = True

        location_fit = city_match or country_match or work_mode_fit
        
        return {
            "location_fit": location_fit,
            "work_mode_fit": work_mode_fit
        }
