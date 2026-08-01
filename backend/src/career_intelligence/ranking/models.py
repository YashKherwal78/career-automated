"""
Opportunity Ranking Models — Phase 3 Ranking Engine

Defines RankingFactor, RankingPolicy, RankedOpportunity, and RankingSnapshot schemas.

Invariant: Ranking metrics produce an opportunity_score for sorting, but NEVER
modify the underlying comparison match score.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RankingFactor(BaseModel):
    """A single factor influencing opportunity ranking."""
    name: str  # "match_score", "company_quality", "response_likelihood", "freshness", "compensation"
    weight: float
    raw_value: float
    weighted_score: float
    explanation: str

    class Config:
        frozen = True


class RankingPolicy(BaseModel):
    """Policy weights for opportunity ranking."""
    policy_id: str = "default_ranking_v1"
    match_score_weight: float = 0.40
    company_quality_weight: float = 0.15
    response_likelihood_weight: float = 0.15
    compensation_weight: float = 0.15
    freshness_weight: float = 0.15

    class Config:
        frozen = True


class RankedOpportunity(BaseModel):
    """An opportunity ranked relative to other opportunities."""
    rank: int
    opportunity_id: str
    job_title: str
    company_name: str

    # Immutable match score from ComparisonEngine
    comparison_match_score: float

    # Deterministically calculated opportunity score for sorting
    opportunity_score: float

    explanation: str
    factors: List[RankingFactor] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class RankingSnapshot(BaseModel):
    """Snapshot of a ranking run for auditability."""
    snapshot_id: str
    generated_at: str
    policy_id: str
    total_opportunities_ranked: int
    rankings: List[RankedOpportunity] = Field(default_factory=list)

    class Config:
        frozen = True
