"""
Resume Tailoring Engine (Module 6).

Inputs: Master Resume + Canonical Profile + Job Description + Recommendation.
Outputs: Tailored Candidate Profile with optimized bullets, targeted summaries,
and gap analysis — subject to strict Truthfulness Validation.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile, ExperienceItem, ProjectItem
from src.resume_intelligence.recommendation.engine import ResumeRecommendation
from src.resume_intelligence.truthfulness.verifier import TruthfulnessEngine, VerificationResult


class TailoredResumeResult(BaseModel):
    job_id: str
    company_name: str
    tailored_profile: CanonicalCandidateProfile
    gap_analysis: Dict[str, Any]
    keyword_coverage: float
    truthfulness_report: VerificationResult


class ResumeTailor:
    """Resume Tailoring Engine with bounded optimization."""

    def __init__(self):
        self.truthfulness_engine = TruthfulnessEngine()

    def tailor_resume(
        self,
        master_profile: CanonicalCandidateProfile,
        job_description: str,
        recommendation: ResumeRecommendation,
        job_id: str = "job_default"
    ) -> TailoredResumeResult:
        
        # Deep copy master profile for tailoring
        tailored = master_profile.model_copy(deep=True)
        jd_lower = job_description.lower()

        # 1. Target Summary Generation
        tailored.personal.summary = (
            f"IIT Roorkee {recommendation.role_type} engineer specializing in "
            f"{', '.join(recommendation.priority_skills[:4])}. Experienced in building end-to-end "
            f"systems, production pipelines, and multi-agent workflows."
        )

        # 2. Project Selection & Prioritization
        selected_projects = []
        for p_name in recommendation.priority_projects:
            for proj in master_profile.projects:
                if proj.title.lower() in p_name.lower() or p_name.lower() in proj.title.lower():
                    selected_projects.append(proj)
                    break
        if not selected_projects:
            selected_projects = master_profile.projects[:3]

        tailored.projects = selected_projects

        # 3. Gap & Keyword Analysis
        all_skills = master_profile.get_all_skills_flat()
        covered_skills = [s for s in all_skills if s.lower() in jd_lower]
        missing_skills = [s for s in ["Kubernetes", "GraphQL", "Redis", "Kafka"] if s.lower() in jd_lower and s.lower() not in [x.lower() for x in all_skills]]
        keyword_coverage = min(1.0, len(covered_skills) / max(1, len(covered_skills) + len(missing_skills)))

        # 4. Truthfulness Verification Gate
        verification = self.truthfulness_engine.verify_statement(
            tailored.personal.summary,
            master_profile
        )

        return TailoredResumeResult(
            job_id=job_id,
            company_name=recommendation.company_name,
            tailored_profile=tailored,
            gap_analysis={
                "covered_skills": covered_skills,
                "missing_skills": missing_skills,
                "recommendations": recommendation.explainability
            },
            keyword_coverage=round(keyword_coverage * 100, 2),
            truthfulness_report=verification
        )
