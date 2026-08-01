"""
Company Intelligence Models — Phase 3 Company Intelligence

Defines CultureMetrics, CompanyProfile, and CompanyRecommendation schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CultureMetrics(BaseModel):
    """Engineering culture metrics for a company."""
    work_life_balance_rating: float = 4.0
    engineering_rigor_rating: float = 4.2
    remote_flexibility: str = "High"
    pace: str = "Fast-Paced"

    class Config:
        frozen = True


class CompanyProfile(BaseModel):
    """Structured company intelligence profile."""
    company_id: str
    company_name: str
    ats_provider: str = "Greenhouse"  # "Greenhouse", "Lever", "Workday", "Ashby"
    hiring_velocity: str = "High"  # "High", "Moderate", "Slow"
    avg_response_days: int = 5
    historical_response_rate: float = 0.25  # 25% callback rate
    hiring_difficulty: str = "Medium"  # "Low", "Medium", "Hard", "Extreme"
    interview_stages: List[str] = Field(default_factory=lambda: [
        "Recruiter Screen",
        "Technical Phone Screen",
        "System Design / Coding Onsite",
        "Behavioral & Executive Round",
    ])
    primary_tech_stack: List[str] = Field(default_factory=list)
    culture: CultureMetrics = Field(default_factory=CultureMetrics)
    recruiter_insights: List[str] = Field(default_factory=list)

    class Config:
        frozen = True


class CompanyRecommendation(BaseModel):
    """Targeting recommendation for a specific company."""
    company_name: str
    recommendation_level: str  # "TOP_TARGET", "HIGH_PROBABILITY", "REACH", "PAUSE"
    reasoning: str
    key_advantages: List[str] = Field(default_factory=list)

    class Config:
        frozen = True
