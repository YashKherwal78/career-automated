"""
Career Memory Models — Phase 3 Memory Store Module

Defines LongitudinalMemory and PreferenceProfile schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class PreferenceProfile(BaseModel):
    """Longitudinal preferences tracked over time."""
    favorite_companies: List[str] = Field(default_factory=list)
    preferred_technologies: List[str] = Field(default_factory=list)
    target_seniority_levels: List[str] = Field(default_factory=list)

    class Config:
        frozen = True


class LongitudinalMemory(BaseModel):
    """Persistent long-term career memory for a candidate."""
    candidate_id: str
    completed_milestones: List[str] = Field(default_factory=list)
    accepted_jobs: List[str] = Field(default_factory=list)
    rejected_jobs: List[str] = Field(default_factory=list)
    preferences: PreferenceProfile = Field(default_factory=PreferenceProfile)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
