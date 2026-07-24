from typing import Dict, Any, List
from src.discovery.jie.models import StructuredJob

class JobFilterEvaluator:
    @staticmethod
    def match_filters(job: StructuredJob, filters: Dict[str, Any]) -> bool:
        """Determines if a StructuredJob matches a set of dashboard filter criteria using canonical values."""
        
        # 1. Location match (Country, State, City)
        if "location" in filters:
            f_loc = filters["location"]
            for key in ["country", "state", "city"]:
                if f_loc.get(key) and f_loc[key].lower() != job.location.get(key, "").lower():
                    return False

        # 2. Work Mode match
        if "work_mode" in filters:
            if filters["work_mode"] != job.work_mode:
                return False

        # 3. Employment Type match
        if "employment_type" in filters:
            if filters["employment_type"] != job.employment_type:
                return False

        # 4. Experience baseline check
        if "experience" in filters:
            f_exp = filters["experience"] # e.g. "Fresher", "0-2 Years", "2-5 Years", "5+ Years"
            min_exp = job.experience_min or 0
            if f_exp == "Fresher":
                if not job.fresher_friendly:
                    return False
            elif f_exp == "0-2 Years":
                if min_exp > 2:
                    return False
            elif f_exp == "2-5 Years":
                if min_exp < 2 or min_exp > 5:
                    return False
            elif f_exp == "5+ Years":
                if min_exp < 5:
                    return False

        # 5. Technology match (must have at least one or all of the filter techs)
        if "technologies" in filters:
            req_techs = [t.lower() for t in filters["technologies"]]
            job_techs = {t.lower() for t in job.technologies}
            if not any(t in job_techs for t in req_techs):
                return False

        # 6. Skill match
        if "skills" in filters:
            req_skills = [s.lower() for s in filters["skills"]]
            job_skills = {s.lower() for s in job.skills}
            if not any(s in job_skills for s in req_skills):
                return False

        return True
