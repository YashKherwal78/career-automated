"""
Resume Intelligence Models — Phase 3 Resume Intelligence

Defines ATSScore, ResumeRecommendation, and ResumeAudit schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ATSScore(BaseModel):
    """Estimated ATS compatibility breakdown."""
    overall_ats_score: float  # 0 to 100
    keyword_density_score: float
    format_parsability_score: float
    section_completeness_score: float

    class Config:
        frozen = True


class ResumeRecommendation(BaseModel):
    """Actionable improvement recommendation for a resume."""
    section: str  # "skills", "experience", "summary", "education"
    issue: str
    recommendation: str
    suggested_keywords: List[str] = Field(default_factory=list)

    class Config:
        frozen = True


class ResumeAudit(BaseModel):
    """Complete resume intelligence audit report."""
    recommended_variant: str
    ats_compatibility: ATSScore
    recommendations: List[ResumeRecommendation] = Field(default_factory=list)
    missing_critical_keywords: List[str] = Field(default_factory=list)
    summary: str = ""

    class Config:
        frozen = True
