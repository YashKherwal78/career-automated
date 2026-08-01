"""
Screening Protocols & Interfaces — Phase 2 Screening Layer

Defines the ScreeningRule interface contract.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from src.career_intelligence.evaluation.models import EvaluationContext
from src.career_intelligence.screening.models import RuleResult


@runtime_checkable
class ScreeningRule(Protocol):
    """Protocol for screening rules.

    Each rule evaluates an EvaluationContext against candidate information
    and returns a tri-state RuleResult (PASS, REJECT, or UNKNOWN).
    """

    def evaluate(
        self,
        context: EvaluationContext,
        candidate_data: Any,
    ) -> RuleResult:
        """Evaluate a single constraint or preference.

        Returns:
            RuleResult with decision PASS, REJECT, or UNKNOWN.
        """
        ...
