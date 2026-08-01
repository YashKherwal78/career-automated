"""
Evaluation Models — EvaluationContext and Policy Types

EvaluationContext is the single semantic representation of a job for
downstream consumers (PreferenceMatcher, EligibilityChecker,
ComparisonEngine). It is derived solely from StructuredJob by the
EvaluationContextResolver.

Includes policy_version for reproducibility (per user feedback).

Invariant: EvaluationContext is immutable once constructed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.career_intelligence.job_intelligence.models import (
    Classification,
    LocationInfo,
    SalaryInfo,
)


class EvaluationPolicy(BaseModel):
    """Defines the evaluation weights and rules for a job family.

    Policies are versioned to support historical reproducibility.
    """
    policy_id: str
    policy_version: str = "1.0"
    job_family: str = "unknown"
    description: str = ""

    # Weights for each scoring dimension (must sum to ~1.0)
    weights: Dict[str, float] = Field(default_factory=lambda: {
        "skills": 0.25,
        "technologies": 0.20,
        "experience": 0.20,
        "domain": 0.10,
        "education": 0.10,
        "seniority": 0.10,
        "location": 0.05,
    })

    # Minimum thresholds for each dimension (0.0 = no minimum)
    thresholds: Dict[str, float] = Field(default_factory=dict)

    class Config:
        frozen = True


class EvaluationContext(BaseModel):
    """The canonical downstream view of a job for evaluation.

    All downstream components (PreferenceMatcher, EligibilityChecker,
    ComparisonEngine) consume this instead of reaching back into
    StructuredJob directly.

    Invariant: Immutable once constructed.
    """
    schema_version: str = "2.0.0"

    # ── Policy ──
    policy: EvaluationPolicy
    policy_version: str = "1.0"  # Duplicated for snapshot convenience

    # ── Job identity ──
    jd_hash: str
    title: str = ""
    company: str = ""

    # ── Semantic classifications ──
    seniority: Classification = Field(
        default_factory=lambda: Classification(value="unknown")
    )
    job_family: Classification = Field(
        default_factory=lambda: Classification(value="unknown")
    )
    domains: List[Classification] = Field(default_factory=list)
    capabilities: List[Classification] = Field(default_factory=list)

    # ── Job parameters ──
    work_mode: str = "Unknown"
    location: LocationInfo = Field(default_factory=LocationInfo)
    compensation: SalaryInfo = Field(default_factory=SalaryInfo)
    employment_type: str = "Unknown"

    # Experience
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    fresher_friendly: bool = False

    # Qualifications
    education_required: List[str] = Field(default_factory=list)
    certifications_required: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)

    # Legal
    visa_sponsorship: str = "Unknown"

    # Traceability
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
