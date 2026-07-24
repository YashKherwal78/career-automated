from typing import Dict, Any, List
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class TechnologyComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares technologies required by job description vs candidate profile technologies."""
        job_techs = {t.lower() for t in job.technologies}
        if not job_techs:
            return {"matched": [], "missing": [], "extra": [], "categories": {}}

        candidate_techs = set()
        for cat in ["programming_languages", "frameworks", "libraries", "databases", "cloud", "ai_ml", "developer_tools"]:
            for t in getattr(profile.skills, cat, []):
                candidate_techs.add(t.lower())

        for exp in profile.experience:
            for t in exp.technologies:
                candidate_techs.add(t.lower())
        for proj in profile.projects:
            for t in proj.technologies:
                candidate_techs.add(t.lower())

        matched = []
        missing = []
        for t in job.technologies:
            if t.lower() in candidate_techs:
                matched.append(t)
            else:
                missing.append(t)

        extra = []
        for t in candidate_techs:
            if t.lower() not in job_techs:
                extra.append(t.title())

        # Simple category tagging
        categories = {}
        for t in job.technologies:
            categories[t] = "Software Engineering"

        return {
            "matched": matched,
            "missing": missing,
            "extra": extra[:15],
            "categories": categories
        }
