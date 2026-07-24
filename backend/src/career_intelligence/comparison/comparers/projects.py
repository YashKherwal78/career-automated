from typing import Dict, Any, List
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class ProjectComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, List[str]]:
        """Evaluates project list of candidate profile against technology tags of the job description."""
        job_techs = {t.lower() for t in job.technologies}
        if not job_techs or not profile.projects:
            return {"matched_projects": [], "relevant_projects": [], "irrelevant_projects": []}
            
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
                
        return {
            "matched_projects": matched,
            "relevant_projects": relevant,
            "irrelevant_projects": irrelevant
        }
