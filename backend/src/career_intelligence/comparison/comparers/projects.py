from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, ProjectComparison
from src.discovery.jie.models import StructuredJob

class ProjectComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> ProjectComparison:
        """Evaluates project list of candidate profile against technology tags of the job description."""
        job_techs = {t.lower() for t in job.technologies}
        if not job_techs or not profile.projects:
            return ProjectComparison(score=1.0, reasoning=["No technology stack project validation required."])
            
        matched = []
        relevant = []
        irrelevant = []
        
        for proj in profile.projects:
            proj_techs = {t.lower() for t in proj.technologies}
            overlap = proj_techs.intersection(job_techs)
            if overlap:
                matched.append(proj.name)
                relevant.append(proj.name)
            else:
                irrelevant.append(proj.name)
                
        total = len(matched) + len(irrelevant)
        score = len(matched) / total if total > 0 else 1.0
        reasoning = [
            f"Candidate has {len(matched)} project(s) matching job technologies."
        ]

        return ProjectComparison(
            score=score,
            matched_projects=matched,
            relevant_projects=relevant,
            irrelevant_projects=irrelevant,
            reasoning=reasoning,
            confidence=0.85
        )
