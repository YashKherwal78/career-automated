from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class ProjectComparer:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Evaluates candidate projects compatibility against job description technology stacks."""
        job_techs = {t.lower() for t in job.technologies}
        if not job_techs or not profile.projects:
            return {
                "score": 1.0,
                "matched_projects": [],
                "reason": "No project technologies overlap check required."
            }

        matched_projects = []
        for proj in profile.projects:
            proj_techs = {t.lower() for t in proj.technologies}
            overlap = proj_techs.intersection(job_techs)
            if overlap:
                matched_projects.append({
                    "name": proj.name,
                    "overlap": list(overlap)
                })

        score = len(matched_projects) / len(profile.projects) if profile.projects else 0.0
        reason = (
            f"Candidate has {len(matched_projects)} project(s) demonstrating relevant technology stacks."
            if matched_projects else "No direct project technology matches."
        )

        return {
            "score": score,
            "matched_projects": matched_projects,
            "reason": reason
        }
