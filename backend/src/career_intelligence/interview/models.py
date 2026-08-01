"""
Interview Intelligence Models — Phase 3 Interview Intelligence

Defines QuestionBank, ConceptWeakness, and InterviewPreparationPlan schemas.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from src.career_intelligence.explainability.models import InterviewQuestion


class ConceptWeakness(BaseModel):
    """Concept area requiring study before interviews."""
    concept_name: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    recommended_study_hours: int = 5
    key_topics: List[str] = Field(default_factory=list)

    class Config:
        frozen = True


class QuestionBank(BaseModel):
    """Collection of interview questions categorized by stage."""
    phone_screen_questions: List[InterviewQuestion] = Field(default_factory=list)
    technical_deep_dive_questions: List[InterviewQuestion] = Field(default_factory=list)
    system_design_questions: List[InterviewQuestion] = Field(default_factory=list)

    class Config:
        frozen = True


class InterviewPreparationPlan(BaseModel):
    """Complete interview intelligence preparation plan."""
    comparison_id: str
    job_title: str
    readiness_confidence: float  # 0 to 100
    question_bank: QuestionBank
    concept_weaknesses: List[ConceptWeakness] = Field(default_factory=list)
    study_roadmap_summary: str = ""

    class Config:
        frozen = True
