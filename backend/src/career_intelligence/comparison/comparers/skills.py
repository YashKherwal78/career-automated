from typing import List
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, SkillComparison
from src.discovery.jie.models import StructuredJob

class SkillComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> SkillComparison:
        """Compares candidate skills against job requirements returning a strongly-typed SkillComparison."""
        job_skills = {s.lower() for s in job.skills}
        if not job_skills:
            return SkillComparison(score=1.0, reasoning=["No skills specified by the job description."])

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
            if len(s) > 10:
                critical.append(s)
            else:
                optional.append(s)

        extra = []
        for s in candidate_skills:
            if s.lower() not in job_skills:
                extra.append(s.title())

        score = len(matched) / len(job_skills)
        reasoning = [
            f"Matched exact professional skill keywords: {', '.join(matched[:3])}" if matched else "No exact skill matches.",
            f"Missing skills: {', '.join(missing[:3])}" if missing else "No missing skills."
        ]

        return SkillComparison(
            score=score,
            matched=matched,
            missing=missing,
            extra_skills=extra[:15],
            critical_missing=critical,
            optional_missing=optional,
            reasoning=reasoning,
            confidence=0.9
        )
