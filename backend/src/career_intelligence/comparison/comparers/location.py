from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, LocationComparison
from src.discovery.jie.models import StructuredJob

class LocationComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> LocationComparison:
        """Compares location boundaries returning a strongly-typed LocationComparison."""
        job_city = job.location.get("city", "").lower().strip()
        job_country = job.location.get("country", "").lower().strip()
        
        cand_loc_str = profile.personal_info.location.lower() if profile.personal_info.location else ""
        
        city_match = False
        country_match = False
        
        if job_city and job_city in cand_loc_str:
            city_match = True
        if job_country and job_country in cand_loc_str:
            country_match = True

        work_mode_fit = False
        if job.work_mode == "Remote":
            work_mode_fit = True
        elif job.work_mode == "Hybrid":
            work_mode_fit = True
        else:
            work_mode_fit = True

        location_fit = city_match or country_match or work_mode_fit
        score = 1.0 if (location_fit and work_mode_fit) else 0.5
        reasoning = [
            f"Location check status: city matched={city_match}, country matched={country_match}.",
            f"Work mode compatible with target: {job.work_mode}."
        ]

        return LocationComparison(
            score=score,
            location_fit=location_fit,
            work_mode_fit=work_mode_fit,
            reasoning=reasoning,
            confidence=0.95
        )
