from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class SkillComparer:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares professional domain skills between candidate profile and structured job description."""
        job_skills = {s.lower() for s in job.skills}
        if not job_skills:
            return {"score": 1.0, "matched": [], "missing": []}

        # Gather all candidate skills across standard descriptors
        candidate_skills = set()
        for s in profile.personal_info.location.split(",") if profile.personal_info.location else []:
            candidate_skills.add(s.strip().lower())
            
        # Add categorized skills
        for cat in ["programming_languages", "frameworks", "libraries", "databases", "cloud", "ai_ml", "developer_tools", "other"]:
            for s in getattr(profile.skills, cat, []):
                candidate_skills.add(s.lower())
                
        # Match
        matched = []
        missing = []
        for s in job.skills:
            if s.lower() in candidate_skills:
                matched.append(s)
            else:
                missing.append(s)
                
        score = len(matched) / len(job_skills)
        return {
            "score": score,
            "matched": matched,
            "missing": missing
        }
