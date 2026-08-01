"""
Analytics Models — Phase 3 Analytics Module

Defines FunnelAnalytics, SkillDemandTrend, and AnalyticsReport schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FunnelAnalytics(BaseModel):
    """Application conversion funnel analytics."""
    total_applications: int = 0
    total_screens: int = 0
    total_interviews: int = 0
    total_offers: int = 0
    overall_conversion_rate: float = 0.0

    class Config:
        frozen = True


class SkillDemandTrend(BaseModel):
    """Market demand trend for a skill or capability."""
    skill_name: str
    demand_level: str  # "HIGH", "MODERATE", "EMERGING"
    percentage_of_jobs_requiring: float

    class Config:
        frozen = True


class AnalyticsReport(BaseModel):
    """Aggregated career intelligence analytics report."""
    candidate_id: str
    funnel: FunnelAnalytics
    avg_match_score: float
    score_distribution: Dict[str, int] = Field(default_factory=dict)
    skill_demand_trends: List[SkillDemandTrend] = Field(default_factory=list)
    summary: str = ""

    class Config:
        frozen = True
