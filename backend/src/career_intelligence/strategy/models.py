"""
Career Strategy Models — Phase 3 Strategy Engine

Defines StrategicAction and CareerStrategy schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class StrategicAction(BaseModel):
    """A concrete tactical action recommended by the strategy engine."""
    category: Literal["DAILY_TARGET", "SKILL_FOCUS", "COMPANY_TARGETING", "PROFILE_IMPROVEMENT", "APPLICATION_PAUSE"]
    headline: str
    rationale: str
    target_items: List[str] = Field(default_factory=list)
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"

    class Config:
        frozen = True


class CareerStrategy(BaseModel):
    """High-level strategic plan for candidate career progression."""
    candidate_id: str
    strategy_summary: str
    actions: List[StrategicAction] = Field(default_factory=list)
    daily_application_goal: int = 10
    current_focus_domain: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
