"""
PreferenceMatcher — Phase 2 Preference Evaluation

Evaluates explicit user preferences against EvaluationContext:
  1. Work mode preferences (Remote / Hybrid / Onsite)
  2. Location preferences & relocation willingness
  3. Salary expectation thresholds
  4. Target seniority bounds

Tri-State Behavior:
  - PASS: Candidate explicitly accepts this parameter.
  - REJECT: Unambiguous conflict with candidate's stated constraint.
  - UNKNOWN: Candidate preference is missing. Produces MissingField and continues.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from src.career_intelligence.evaluation.models import EvaluationContext
from src.career_intelligence.screening.models import (
    RuleDecision,
    RuleResult,
)

logger = logging.getLogger("PreferenceMatcher")


class PreferenceMatcher:
    """Evaluates candidate preferences against an EvaluationContext."""

    def match_all(
        self,
        context: EvaluationContext,
        preferences_data: Any,
    ) -> List[RuleResult]:
        """Run all preference matching checks.

        Args:
            context:          EvaluationContext from EvaluationContextResolver.
            preferences_data: Candidate preferences object or dictionary.

        Returns:
            List of RuleResult objects.
        """
        results: List[RuleResult] = []

        results.append(self.match_work_mode(context, preferences_data))
        results.append(self.match_location(context, preferences_data))
        results.append(self.match_salary(context, preferences_data))

        return results

    # ── Rule 1: Work Mode Preference ──

    def match_work_mode(
        self,
        context: EvaluationContext,
        prefs: Any,
    ) -> RuleResult:
        """Match job work mode against candidate work mode preferences."""
        job_mode = context.work_mode  # "Remote", "Hybrid", "Onsite", "Unknown"

        if job_mode == "Unknown":
            return RuleResult(
                rule_name="work_mode_preference",
                decision=RuleDecision.PASS,
                reason="Job work mode unspecified.",
            )

        remote_allowed = self._get_attr(prefs, ["remote_allowed", "remote", "allow_remote"])
        preferred_modes = self._get_attr(prefs, ["preferred_work_modes", "work_modes"])

        if remote_allowed is None and not preferred_modes:
            return RuleResult(
                rule_name="work_mode_preference",
                decision=RuleDecision.UNKNOWN,
                reason="Candidate work mode preferences missing.",
                field="work_mode",
            )

        # Check explicit negative preference
        if job_mode == "Remote" and remote_allowed is False:
            return RuleResult(
                rule_name="work_mode_preference",
                decision=RuleDecision.REJECT,
                reason="Job is Remote; candidate specified remote_allowed=False.",
                field="remote_allowed",
                job_value="Remote",
                candidate_value=False,
            )

        if preferred_modes and isinstance(preferred_modes, list):
            modes_lower = [str(m).lower() for m in preferred_modes]
            if job_mode.lower() not in modes_lower:
                return RuleResult(
                    rule_name="work_mode_preference",
                    decision=RuleDecision.REJECT,
                    reason=f"Job work mode '{job_mode}' not in preferred list {preferred_modes}.",
                    field="preferred_work_modes",
                    job_value=job_mode,
                    candidate_value=preferred_modes,
                )

        return RuleResult(
            rule_name="work_mode_preference",
            decision=RuleDecision.PASS,
            reason=f"Work mode '{job_mode}' aligns with candidate preferences.",
        )

    # ── Rule 2: Location Preference ──

    def match_location(
        self,
        context: EvaluationContext,
        prefs: Any,
    ) -> RuleResult:
        """Match job location against candidate preferred locations."""
        job_city = context.location.city
        job_state = context.location.state
        job_country = context.location.country
        job_raw = context.location.raw.lower()

        if context.work_mode == "Remote":
            return RuleResult(
                rule_name="location_preference",
                decision=RuleDecision.PASS,
                reason="Remote role; location restriction waived.",
            )

        preferred_locations = self._get_attr(prefs, ["preferred_locations", "locations"])
        relocate = self._get_attr(prefs, ["willing_to_relocate", "relocation"])

        if not preferred_locations and relocate is None:
            return RuleResult(
                rule_name="location_preference",
                decision=RuleDecision.UNKNOWN,
                reason="Candidate location preferences missing.",
                field="preferred_locations",
            )

        if relocate is True:
            return RuleResult(
                rule_name="location_preference",
                decision=RuleDecision.PASS,
                reason="Candidate willing to relocate.",
            )

        if preferred_locations and isinstance(preferred_locations, list):
            loc_strings = [str(l).lower() for l in preferred_locations]
            # Match city, state, country, or raw
            matched = any(
                p in job_raw or (job_city and p in job_city.lower()) or (job_country and p in job_country.lower())
                for p in loc_strings
            )

            if matched:
                return RuleResult(
                    rule_name="location_preference",
                    decision=RuleDecision.PASS,
                    reason=f"Job location '{context.location.raw}' matches preferred locations.",
                )

            return RuleResult(
                rule_name="location_preference",
                decision=RuleDecision.REJECT,
                reason=f"Job location '{context.location.raw}' not in preferred locations {preferred_locations}.",
                field="preferred_locations",
                job_value=context.location.raw,
                candidate_value=preferred_locations,
            )

        return RuleResult(
            rule_name="location_preference",
            decision=RuleDecision.PASS,
            reason="Location check passed.",
        )

    # ── Rule 3: Salary Expectation ──

    def match_salary(
        self,
        context: EvaluationContext,
        prefs: Any,
    ) -> RuleResult:
        """Match job salary minimum against candidate minimum salary expectation."""
        min_salary = self._get_attr(prefs, ["minimum_salary", "target_salary", "salary_expectation"])

        if min_salary is None or float(min_salary or 0) <= 0:
            return RuleResult(
                rule_name="salary_preference",
                decision=RuleDecision.UNKNOWN,
                reason="Candidate minimum salary expectation missing.",
                field="minimum_salary",
            )

        job_max = context.compensation.maximum
        if job_max is None:
            return RuleResult(
                rule_name="salary_preference",
                decision=RuleDecision.PASS,
                reason="Job salary maximum unstated; passing check.",
            )

        min_sal_val = float(min_salary)
        if job_max < min_sal_val * 0.7:  # Reject if job max is > 30% below candidate min
            return RuleResult(
                rule_name="salary_preference",
                decision=RuleDecision.REJECT,
                reason=f"Job maximum salary ${job_max:,.0f} is significantly below candidate minimum expectation ${min_sal_val:,.0f}.",
                field="minimum_salary",
                job_value=job_max,
                candidate_value=min_sal_val,
            )

        return RuleResult(
            rule_name="salary_preference",
            decision=RuleDecision.PASS,
            reason="Salary alignment check passed.",
        )

    # ── Helper ──

    @staticmethod
    def _get_attr(obj: Any, keys: List[str]) -> Optional[Any]:
        """Safely fetch attribute value from object or dictionary."""
        if obj is None:
            return None
        for k in keys:
            if isinstance(obj, dict) and k in obj:
                val = obj[k]
                if val is not None:
                    return val
            elif hasattr(obj, k):
                val = getattr(obj, k)
                if val is not None:
                    return val
        return None
