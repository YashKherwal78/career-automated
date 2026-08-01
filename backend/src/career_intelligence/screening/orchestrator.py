"""
ScreeningOrchestrator — Phase 2 Screening Layer Orchestrator

Sequentially executes EligibilityChecker and PreferenceMatcher against an
EvaluationContext and candidate data, returning a descriptive ScreeningResult.

Deterministic Logic:
  - If any check returns REJECT -> overall = "REJECT"
  - Otherwise -> overall = "PASS"
  - UNKNOWN results generate MissingField entries in 'unknown', but do NOT
    cause overall REJECT.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from src.career_intelligence.evaluation.models import EvaluationContext
from src.career_intelligence.screening.eligibility import EligibilityChecker
from src.career_intelligence.screening.models import (
    MissingField,
    RuleDecision,
    RuleResult,
    ScreeningResult,
)
from src.career_intelligence.screening.preferences import PreferenceMatcher

logger = logging.getLogger("ScreeningOrchestrator")


class ScreeningOrchestrator:
    """Coordinates screening rules and builds deterministic ScreeningResult."""

    def __init__(self) -> None:
        self._eligibility_checker = EligibilityChecker()
        self._preference_matcher = PreferenceMatcher()

    def screen(
        self,
        context: EvaluationContext,
        candidate_profile: Any,
        candidate_preferences: Optional[Any] = None,
        candidate_eligibility: Optional[Any] = None,
    ) -> ScreeningResult:
        """Screen a job EvaluationContext against candidate models.

        Args:
            context:               EvaluationContext for the job.
            candidate_profile:     CandidateProfile or candidate data object.
            candidate_preferences: CandidatePreferences object (optional).
            candidate_eligibility: CandidateEligibility object (optional).

        Returns:
            Descriptive, deterministic ScreeningResult (overall PASS or REJECT).
        """
        # Fall back to candidate_profile if sub-objects are not provided
        prefs_target = candidate_preferences if candidate_preferences is not None else candidate_profile
        elig_target = candidate_eligibility if candidate_eligibility is not None else candidate_profile

        # 1. Collect rule evaluations
        rule_results: List[RuleResult] = []
        rule_results.extend(self._eligibility_checker.check_all(context, elig_target))
        rule_results.extend(self._preference_matcher.match_all(context, prefs_target))

        # 2. Bucket outcomes
        matched: List[str] = []
        conflicts: List[str] = []
        unknown: List[MissingField] = []

        for res in rule_results:
            if res.decision == RuleDecision.PASS:
                matched.append(res.rule_name)
            elif res.decision == RuleDecision.REJECT:
                conflicts.append(f"[{res.rule_name}] {res.reason}")
            elif res.decision == RuleDecision.UNKNOWN:
                field_name = res.field or res.rule_name
                unknown.append(
                    MissingField(field=field_name, reason=res.reason)
                )

        # 3. Determine overall state deterministically
        overall_status: Literal["PASS", "REJECT"] = "REJECT" if len(conflicts) > 0 else "PASS"

        logger.info(
            "ScreeningOrchestrator: jd_hash=%s → overall=%s (matched=%d, conflicts=%d, unknown=%d)",
            context.jd_hash,
            overall_status,
            len(matched),
            len(conflicts),
            len(unknown),
        )

        return ScreeningResult(
            overall=overall_status,
            matched=matched,
            conflicts=conflicts,
            unknown=unknown,
            metadata={
                "total_rules_evaluated": len(rule_results),
                "context_policy": context.policy.policy_id,
            },
        )
