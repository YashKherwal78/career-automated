"""
Screening Layer Models — Phase 2 Screening Layer

Defines MissingField, RuleDecision, and ScreeningResult schemas.

Philosophical Invariant:
  - Screening eliminates ONLY jobs that are confidently impossible or explicitly
    outside user-stated constraints.
  - UNKNOWN always continues. Missing facts produce MissingField entries in the
    'unknown' list, but NEVER trigger an overall REJECT.
  - overall is strictly Literal["PASS", "REJECT"].
    If conflicts is non-empty -> REJECT.
    Else -> PASS.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RuleDecision(str, Enum):
    """Tri-state rule evaluation result."""
    PASS = "PASS"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


class MissingField(BaseModel):
    """Describes missing candidate/job data for progressive profiling."""
    field: str
    reason: str

    class Config:
        frozen = True


class RuleResult(BaseModel):
    """Outcome of a single screening rule evaluation."""
    rule_name: str
    decision: RuleDecision
    reason: str = ""
    field: str = ""
    job_value: Any = None
    candidate_value: Any = None

    class Config:
        frozen = True


class ScreeningResult(BaseModel):
    """Descriptive outcome of the candidate screening evaluation.

    Contains:
      - overall: Literal["PASS", "REJECT"] (REJECT if conflicts > 0 else PASS)
      - matched: list of rule names or dimension labels that passed
      - conflicts: list of rule failure explanations that triggered REJECT
      - unknown: list of MissingField items for missing candidate/job information
      - metadata: execution audit info

    Invariant: Descriptive only. The orchestrator makes routing decisions.
    """
    overall: Literal["PASS", "REJECT"]
    matched: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    unknown: List[MissingField] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        frozen = True
