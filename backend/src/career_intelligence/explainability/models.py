"""
Explainability Models — Phase 2 Explainability & Recruiter Intelligence

Defines EvidenceItem, EvidenceReport, InterviewQuestion, and RecruiterSummary schemas.

Invariant: Explainability models contain NO mutable score calculation fields.
They purely structure explanations derived from ComparisonResult and ComparisonSnapshot.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """A single item of evidence explaining a match component."""
    category: Literal[
        "strength",
        "weakness",
        "missing_capability",
        "positive_semantic_match",
        "screening_observation",
    ]
    title: str
    description: str
    source_field: str = ""
    weight: float = 1.0
    confidence: float = 1.0

    class Config:
        frozen = True


class EvidenceReport(BaseModel):
    """Structured report explaining why scores were assigned."""
    comparison_id: str
    snapshot_id: str
    overall_score: float
    screening_status: str

    strengths: List[EvidenceItem] = Field(default_factory=list)
    weaknesses: List[EvidenceItem] = Field(default_factory=list)
    missing_capabilities: List[EvidenceItem] = Field(default_factory=list)
    positive_semantic_matches: List[EvidenceItem] = Field(default_factory=list)
    screening_observations: List[EvidenceItem] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True


class InterviewQuestion(BaseModel):
    """Suggested interview question targeted at candidate gaps or verification."""
    topic: str
    question: str
    focus_area: str  # "technical_depth", "experience_verification", "domain_knowledge"
    difficulty: str = "medium"

    class Config:
        frozen = True


class RecruiterSummary(BaseModel):
    """Recruiter-facing summary derived from comparison evidence."""
    comparison_id: str
    job_title: str
    overall_recommendation: Literal["STRONG_HIRE", "HIRE", "CONSIDER", "DO_NOT_ADVANCE"]
    overall_score: float

    executive_summary: str
    top_strengths: List[str] = Field(default_factory=list)
    primary_concerns: List[str] = Field(default_factory=list)
    interview_focus_areas: List[InterviewQuestion] = Field(default_factory=list)

    class Config:
        frozen = True
