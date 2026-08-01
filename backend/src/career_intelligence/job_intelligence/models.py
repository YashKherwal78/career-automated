"""
Job Intelligence Models — Phase 2 Ingestion Layer

Defines the two-stage job representation:
  ParsedJob  — raw facts extracted verbatim from job text (immutable)
  StructuredJob — semantically enriched canonical representation (immutable)

Also defines Classification (generic value + confidence wrapper) and
the Seniority enum used across the pipeline.

Invariant: Both ParsedJob and StructuredJob are frozen after construction.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class Seniority(str, Enum):
    """Canonical seniority levels used across the pipeline."""
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    STAFF = "staff"
    PRINCIPAL = "principal"
    DIRECTOR = "director"
    VP = "vp"
    C_LEVEL = "c_level"
    UNKNOWN = "unknown"


class Classification(BaseModel):
    """Generic value + confidence wrapper.

    Used everywhere a classifier produces a result so that downstream
    consumers can inspect how confident the enricher was.
    """
    value: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)

    class Config:
        frozen = True


# ---------------------------------------------------------------------------
# ParsedJob — Stage 1 output (raw extraction, no inference)
# ---------------------------------------------------------------------------

class SalaryInfo(BaseModel):
    """Raw salary data extracted from a job description."""
    currency: str = ""
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    period: str = ""  # "annual", "monthly", "hourly"

    class Config:
        frozen = True


class LocationInfo(BaseModel):
    """Structured location extracted from a job description."""
    country: str = ""
    state: str = ""
    city: str = ""
    raw: str = ""  # original string before parsing

    class Config:
        frozen = True


class ParsedRequirement(BaseModel):
    """A single requirement extracted from the JD with provenance."""
    category: str  # "skill", "experience", "education", "domain", "certification"
    name: str
    importance: str = "REQUIRED"  # "REQUIRED", "PREFERRED", "OPTIONAL"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    evidence: str = ""  # raw snippet from JD

    class Config:
        frozen = True


class ParsedJob(BaseModel):
    """Stage 1: Raw facts extracted verbatim from the job text.

    No semantic inference happens here — only pattern extraction.
    Produced by JobParser and consumed by JobEnricher.

    Invariant: Immutable once constructed.
    """
    schema_version: str = "2.0.0"
    jd_hash: str
    parsed_at: str  # ISO 8601

    # Core fields
    title: str = ""
    company: str = ""
    job_url: str = ""
    job_id: str = ""

    # Location
    location: LocationInfo = Field(default_factory=LocationInfo)
    work_mode: str = "Unknown"  # "Remote", "Onsite", "Hybrid", "Unknown"
    employment_type: str = "Unknown"  # "Full-time", "Part-time", "Contract", "Internship"

    # Experience
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    fresher_friendly: bool = False

    # Compensation
    salary: SalaryInfo = Field(default_factory=SalaryInfo)

    # Qualifications
    education: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    requirements: List[ParsedRequirement] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    certifications_required: List[str] = Field(default_factory=list)

    # Visa / Sponsorship
    visa_sponsorship: str = "Unknown"  # "Yes", "No", "Unknown"

    # Dates
    posted_date: Optional[str] = None
    application_deadline: Optional[str] = None

    # Raw domain hint from metadata (not inferred)
    domain_hint: str = "Unknown"

    # Parser-specific metadata
    parser_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


# ---------------------------------------------------------------------------
# StructuredJob — Stage 2 output (semantically enriched)
# ---------------------------------------------------------------------------

class StructuredJob(BaseModel):
    """Stage 2: Semantically enriched canonical job representation.

    Produced by JobEnricher from a ParsedJob. Contains all inferred
    classifications (seniority, domains, capabilities, job family).

    This is the canonical downstream representation consumed by
    EvaluationContextResolver and the rest of the pipeline.

    Invariant: Immutable once constructed.
    """
    schema_version: str = "2.0.0"

    # ── Carry-forward from ParsedJob ──
    jd_hash: str
    parsed_at: str

    title: str = ""
    company: str = ""
    job_url: str = ""
    job_id: str = ""

    location: LocationInfo = Field(default_factory=LocationInfo)
    work_mode: str = "Unknown"
    employment_type: str = "Unknown"

    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    fresher_friendly: bool = False

    salary: SalaryInfo = Field(default_factory=SalaryInfo)

    education: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    requirements: List[ParsedRequirement] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    certifications_required: List[str] = Field(default_factory=list)

    visa_sponsorship: str = "Unknown"

    posted_date: Optional[str] = None
    application_deadline: Optional[str] = None

    # ── Enriched classifications ──
    seniority: Classification = Field(
        default_factory=lambda: Classification(value=Seniority.UNKNOWN.value)
    )
    domains: List[Classification] = Field(default_factory=list)
    capabilities: List[Classification] = Field(default_factory=list)
    job_family: Classification = Field(
        default_factory=lambda: Classification(value="unknown")
    )

    # Enrichment metadata
    enricher_version: str = "1.0.0"
    parser_metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
