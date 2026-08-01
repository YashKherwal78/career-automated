"""
Candidate Intelligence Models — Phase 2 Candidate Analysis Layer

Defines CandidateContext: the computed representation derived solely from
a CandidateProfile by CandidateAnalyzer.

CandidateContext contains derived facts (inferred seniority level, primary
domains, capabilities vector, total normalized experience years). It is NOT
a user profile model and contains NO evaluation or match scores.

Invariant: CandidateContext is immutable once constructed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.career_intelligence.job_intelligence.models import (
    Classification,
    Seniority,
)


class CandidateContext(BaseModel):
    """Immutable derived artifact computed from CandidateProfile.

    Derived solely from raw profile data. Consumed by ComparisonEngine,
    PreferenceMatcher, and EligibilityChecker.

    Invariant: Immutable once constructed.
    """
    schema_version: str = "2.0.0"

    # Inferred seniority level derived from experience history
    inferred_level: Classification = Field(
        default_factory=lambda: Classification(value=Seniority.UNKNOWN.value)
    )

    # Inferred primary domain expertise
    primary_domains: List[Classification] = Field(default_factory=list)

    # Normalized capability vector (skills + technologies + frameworks)
    capability_vector: List[Classification] = Field(default_factory=list)

    # Total calculated years of relevant experience
    years_experience: float = 0.0

    # Highest education level attained
    education_level: str = "None"

    # Locations extracted/normalized from profile
    current_location: str = ""

    # Processing metadata
    analyzer_version: str = "1.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
