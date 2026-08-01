"""
Learning Planner Models — Phase 2 Learning Roadmap Layer

Defines LearningMilestone, LearningPath, RoadmapPlan, and LearningNode schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class LearningNode(BaseModel):
    """A node in a learning graph."""
    id: str
    name: str
    prerequisites: List[str] = Field(default_factory=list)
    description: str = ""

    class Config:
        frozen = True


class LearningMilestone(BaseModel):
    """A single milestone step in a capability learning roadmap."""
    capability: str
    category: str = "skill"
    prerequisites: List[str] = Field(default_factory=list)
    estimated_effort_hours: int = 20
    impact_score: float = 0.8
    priority: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "HIGH"
    reasoning: str = ""

    class Config:
        frozen = True


class LearningPath(BaseModel):
    """A structured learning path for a candidate gap."""
    target_role: str
    milestones: List[LearningMilestone] = Field(default_factory=list)
    total_estimated_hours: int = 0
    expected_eligibility_gain: float = 0.0

    class Config:
        frozen = True


class RoadmapPlan(BaseModel):
    """Complete learning roadmap generated for a comparison result."""
    comparison_id: str
    primary_path: LearningPath
    alternative_paths: List[LearningPath] = Field(default_factory=list)
    summary: str = ""

    class Config:
        frozen = True
