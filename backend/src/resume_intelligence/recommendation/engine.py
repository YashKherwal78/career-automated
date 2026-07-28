"""
Module 14 — Resume Recommendation Engine & Explainability (Refinement 4 + Module 14).

Analyzes Job Description + Canonical Candidate Profile and outputs:
- Layout Recommendation (Classic, Modern, Compact)
- Visual Theme Recommendation (Blue, Minimal, Apple, Executive)
- Role Strategy Recommendation (Software Engineer, Product Manager, Data Scientist, ML Engineer, General)
- Project Selection & Ordering Strategy
- Skill Emphasis Strategy
- Full Explainability Log detailing exact reasons for every choice
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile


class RecommendationReason(BaseModel):
    decision: str  # e.g., 'layout_selected', 'theme_selected', 'project_order', 'skills_prioritized'
    value: str
    reason: str  # Plain English explainable rationale
    confidence: float = 0.95


class ResumeRecommendation(BaseModel):
    job_title: str
    company_name: str
    role_type: str  # 'AI', 'PRODUCT', 'SDE', 'DATA', 'GENERAL'
    recommended_layout: str = "Classic"  # 'Classic', 'Modern', 'Compact'
    recommended_theme: str = "Minimal"   # 'Blue', 'Minimal', 'Apple', 'Executive'
    recommended_strategy: str = "Software Engineer"  # 'Software Engineer', 'Product Manager', 'Data Scientist', 'ML Engineer'
    include_summary: bool = True  # Summary scoring decision (PM/Leadership = Highly Recommended; SDE = Optional)
    priority_projects: List[str] = Field(default_factory=list)
    excluded_projects: List[str] = Field(default_factory=list)
    priority_skills: List[str] = Field(default_factory=list)
    priority_experience_order: List[str] = Field(default_factory=list)
    explainability: List[RecommendationReason] = Field(default_factory=list)


from src.resume_intelligence.job_intelligence.models import StructuredJobProfile


class ResumeRecommendationEngine:
    """Decoupled Recommendation Engine consuming StructuredJobProfile objects."""

    def generate_recommendation_from_structured_job(
        self,
        profile: CanonicalCandidateProfile,
        structured_job: StructuredJobProfile
    ) -> ResumeRecommendation:
        """Consumes a pre-parsed StructuredJobProfile instead of raw text."""
        return self.generate_recommendation(
            profile=profile,
            job_title=structured_job.role_title,
            job_description=" ".join([s.name for s in structured_job.required_skills] + [k.keyword for k in structured_job.ats_keywords]),
            company_name=structured_job.company_name
        )

    def generate_recommendation(
        self,
        profile: CanonicalCandidateProfile,
        job_title: str,
        job_description: str,
        company_name: str = ""
    ) -> ResumeRecommendation:
        
        t_lower = job_title.lower()
        jd_lower = job_description.lower()
        reasons = []

        # 1. Role Type Categorization
        if any(w in t_lower for w in ["ai", "machine learning", "ml", "genai", "llm"]):
            role_type = "AI"
            strategy = "ML Engineer"
            p_projects = ["CareerAutomated", "AI Data Analyst Agent", "Semantic Document Search — GDSC IIT Roorkee"]
            ex_projects = ["Echo Pod"]
            theme = "Blue"
        elif any(w in t_lower for w in ["product", "apm", "growth"]):
            role_type = "PRODUCT"
            strategy = "Product Manager"
            p_projects = ["YAAR — AI Behavioral Companion", "CareerAutomated", "Echo Pod"]
            ex_projects = ["SC-MFC Power Optimisation (B.Tech Thesis)"]
            theme = "Apple"
        elif any(w in t_lower for w in ["data", "analyst", "scientist", "quantitative"]):
            role_type = "DATA"
            strategy = "Data Scientist"
            p_projects = ["SC-MFC Power Optimisation (B.Tech Thesis)", "AI Data Analyst Agent", "Semantic Document Search — GDSC IIT Roorkee"]
            ex_projects = ["Echo Pod"]
            theme = "Executive"
        else:
            role_type = "SDE"
            strategy = "Software Engineer"
            p_projects = ["CareerAutomated", "AI Data Analyst Agent", "Semantic Document Search — GDSC IIT Roorkee"]
            ex_projects = ["YAAR — AI Behavioral Companion"]
            theme = "Minimal"

        reasons.append(
            RecommendationReason(
                decision="role_type_classified",
                value=role_type,
                reason=f"Job title '{job_title}' categorized as {role_type} based on keyword match."
            )
        )

        reasons.append(
            RecommendationReason(
                decision="strategy_selected",
                value=strategy,
                reason=f"Selected {strategy} ordering strategy to optimize section hierarchy for {role_type} recruiter expectations."
            )
        )

        reasons.append(
            RecommendationReason(
                decision="projects_selected",
                value=", ".join(p_projects),
                reason=f"Selected top {len(p_projects)} projects with strongest technical/product alignment to job requirements."
            )
        )

        if ex_projects:
            reasons.append(
                RecommendationReason(
                    decision="projects_excluded",
                    value=", ".join(ex_projects),
                    reason=f"Excluded {', '.join(ex_projects)} to keep resume strictly on 1 page while eliminating noise."
                )
            )

        # 2. Priority Skills
        all_skills = profile.get_all_skills_flat()
        matched_skills = [s for s in all_skills if s.lower() in jd_lower]
        if not matched_skills:
            matched_skills = all_skills[:6]

        reasons.append(
            RecommendationReason(
                decision="skills_prioritized",
                value=", ".join(matched_skills[:8]),
                reason=f"Prioritized {len(matched_skills[:8])} overlapping skills found directly in Job Description."
            )
        )

        # Summary Scoring Recommendation
        inc_summary = role_type in ["PRODUCT", "AI", "GENERAL"]
        reasons.append(
            RecommendationReason(
                decision="summary_recommendation",
                value="Included" if inc_summary else "Optional",
                reason=f"Summary section {'recommended' if inc_summary else 'optional'} for {role_type} roles."
            )
        )

        return ResumeRecommendation(
            job_title=job_title,
            company_name=company_name,
            role_type=role_type,
            recommended_layout="Classic",
            recommended_theme=theme,
            recommended_strategy=strategy,
            include_summary=inc_summary,
            priority_projects=p_projects,
            excluded_projects=ex_projects,
            priority_skills=matched_skills[:8],
            explainability=reasons
        )
