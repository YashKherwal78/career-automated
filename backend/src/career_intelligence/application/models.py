"""
Application Intelligence Models — Phase 3 Application Intelligence

Defines ApplicationRecord and ApplicationInsights schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ApplicationRecord(BaseModel):
    """Record of a job application."""
    application_id: str
    job_title: str
    company_name: str
    applied_at: str
    status: Literal["APPLIED", "RECRUITER_SCREEN", "TECHNICAL_INTERVIEW", "OFFER", "REJECTED"] = "APPLIED"
    rejection_reason: Optional[str] = None
    comparison_score: float = 0.0

    class Config:
        frozen = True


class ApplicationInsights(BaseModel):
    """Synthesized insights from application history."""
    candidate_id: str
    total_applications: int
    interview_callback_rate: float  # e.g. 0.20 (20%)
    top_performing_company_types: List[str] = Field(default_factory=list)
    rejection_patterns: List[str] = Field(default_factory=list)
    strategic_recommendations: List[str] = Field(default_factory=list)

    class Config:
        frozen = True
