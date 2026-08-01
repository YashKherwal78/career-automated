"""
Feedback Learning Models — Phase 3 Feedback Learning

Defines FeedbackEvent and PolicyAdjustment schemas.
"""

from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class FeedbackEvent(BaseModel):
    """An empirical outcome event recorded from application interactions."""
    event_id: str
    candidate_id: str
    job_id: str
    outcome: Literal["OFFER", "INTERVIEW", "RECRUITER_RESPONSE", "OA", "REJECTED"]
    matched_score: float
    recorded_at: str

    class Config:
        frozen = True


class PolicyAdjustment(BaseModel):
    """Refinement applied to ranking policy weights based on feedback events."""
    policy_id: str
    previous_response_weight: float
    adjusted_response_weight: float
    adjustment_reason: str

    class Config:
        frozen = True
