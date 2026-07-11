from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.discovery.jie.models import StructuredJob, CandidateFit, FitDetail, SkillGap

class CandidateProfile(BaseModel):
    role_families: List[str] = Field(default_factory=list)
    experience_years: int = 0
    skills: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote: bool = True
    employment: List[str] = Field(default_factory=list)

class FitAnalyzer:
    def __init__(self, profile: CandidateProfile):
        self.profile = profile

    def analyze(self, job: StructuredJob) -> CandidateFit:
        fit = CandidateFit()
        
        # 1. Experience Fit
        if job.experience_min is not None:
            if self.profile.experience_years < job.experience_min:
                fit.experience = FitDetail(
                    fit=False,
                    score=0.0,
                    reason=f"Requires minimum {job.experience_min} years, profile has {self.profile.experience_years}."
                )
            else:
                fit.experience = FitDetail(
                    fit=True,
                    score=1.0,
                    reason=f"Profile experience ({self.profile.experience_years}y) meets requirement ({job.experience_min}y)."
                )
        else:
            fit.experience = FitDetail(fit=True, score=1.0, reason="No strict experience minimum detected.")

        # 2. Skill Fit
        matched_skills = []
        missing_skills = []
        total_req = 0
        
        profile_skills_lower = [s.lower() for s in self.profile.skills]
        
        for req in job.requirements:
            if req.type == "skill" and req.importance == "REQUIRED":
                total_req += 1
                if req.name.lower() in profile_skills_lower:
                    matched_skills.append(req.name)
                else:
                    missing_skills.append(req.name)
                    fit.missing_requirements.append(req.name)
                    
        coverage = len(matched_skills) / total_req if total_req > 0 else 1.0
        fit.skills = SkillGap(
            matched=matched_skills,
            missing=missing_skills,
            coverage=coverage
        )
        
        # Calculate overall score
        fit.overall_fit_score = (fit.experience.score * 0.4) + (coverage * 0.6)
        
        return fit
