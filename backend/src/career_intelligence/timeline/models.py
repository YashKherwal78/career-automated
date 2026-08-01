"""
Career Timeline Models — Phase 3 Timeline Module

Defines TimelineSnapshot, ProgressReport, and CareerTimeline schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class TimelineSnapshot(BaseModel):
    """Historical snapshot recorded in the career timeline."""
    snapshot_id: str
    recorded_at: str
    inferred_seniority: str
    capability_count: int
    avg_match_score: float
    unlocked_opportunities_count: int

    class Config:
        frozen = True


class ProgressReport(BaseModel):
    """Progress report comparing two points in time."""
    candidate_id: str
    timespan_days: int
    score_delta: float
    new_capabilities_learned: List[str] = Field(default_factory=list)
    new_opportunities_unlocked: int = 0
    summary: str = ""

    class Config:
        frozen = True


class CareerTimeline(BaseModel):
    """Complete candidate longitudinal timeline."""
    candidate_id: str
    history: List[TimelineSnapshot] = Field(default_factory=list)
    milestones_achieved: List[str] = Field(default_factory=list)

    class Config:
        frozen = True
