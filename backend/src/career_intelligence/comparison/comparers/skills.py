from typing import Dict, Any, List
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class SkillComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, List[str]]:
        """Compares candidate skills against job requirements."""
        job_skills = {s.lower() for s in job.skills}
        if not job_skills:
            return {"matched": [], "missing": [], "extra": [], "critical_missing": [], "optional_missing": []}

        # Candidate skills
        candidate_skills = set()
        for cat in ["programming_languages", "frameworks", "libraries", "databases", "cloud", "ai_ml", "developer_tools", "other"]:
            for s in getattr(profile.skills, cat, []):
                candidate_skills.add(s.lower())

        matched = []
        missing = []
        for s in job.skills:
            if s.lower() in candidate_skills:
                matched.append(s)
            else:
                missing.append(s)

        # Critical missing skills vs optional
        critical = []
        optional = []
        for s in missing:
            # Simple heuristic: longer skills or specific keywords are critical
            if len(s) > 10:
                critical.append(s)
            else:
                optional.append(s)

        extra = []
        for s in candidate_skills:
            if s.lower() not in job_skills:
                extra.append(s.title())

        return {
            "matched": matched,
            "missing": missing,
            "extra": extra[:15],
            "critical_missing": critical,
            "optional_missing": optional
        }
