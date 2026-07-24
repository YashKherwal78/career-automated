from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class TechnologyComparer:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares technologies required by job vs those possessed by the candidate."""
        job_techs = {t.lower() for t in job.technologies}
        if not job_techs:
            return {"score": 1.0, "matched": [], "missing": []}

        # Gather all candidate technologies
        candidate_techs = set()
        for cat in ["programming_languages", "frameworks", "libraries", "databases", "cloud", "ai_ml", "developer_tools"]:
            for t in getattr(profile.skills, cat, []):
                candidate_techs.add(t.lower())
                
        # Include technologies mentioned in experience bullet points or projects
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

        score = len(matched) / len(job_techs)
        return {
            "score": score,
            "matched": matched,
            "missing": missing
        }
