"""
EligibilityChecker — Phase 2 Candidate Eligibility Verification

Evaluates strict legal/practical eligibility constraints against EvaluationContext:
  1. Citizenship requirements
  2. Visa sponsorship constraints
  3. Security clearance requirements

Tri-State Behavior:
  - PASS: Legal requirement satisfied, or role has no restriction.
  - REJECT: Unambiguous conflict with candidate facts.
  - UNKNOWN: Candidate legal status is unpopulated (None). Produces MissingField
    item and continues pipeline (does NOT reject).
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from src.career_intelligence.evaluation.models import EvaluationContext
from src.career_intelligence.screening.models import (
    MissingField,
    RuleDecision,
    RuleResult,
)

logger = logging.getLogger("EligibilityChecker")


class EligibilityChecker:
    """Evaluates legal and physical eligibility constraints."""

    def check_all(
        self,
        context: EvaluationContext,
        eligibility_data: Any,
    ) -> List[RuleResult]:
        """Run all legal eligibility checks.

        Args:
            context:          EvaluationContext from EvaluationContextResolver.
            eligibility_data: Candidate profile/eligibility object.

        Returns:
            List of RuleResult instances.
        """
        results: List[RuleResult] = []

        results.append(self.check_citizenship(context, eligibility_data))
        results.append(self.check_visa_sponsorship(context, eligibility_data))
        results.append(self.check_security_clearance(context, eligibility_data))

        return results

    # ── Rule 1: Citizenship ──

    def check_citizenship(
        self,
        context: EvaluationContext,
        eligibility: Any,
    ) -> RuleResult:
        """Verify citizenship constraints."""
        required = getattr(context, "citizenship_required", None)
        # Check metadata or job text for citizenship rules
        meta_cit = context.metadata.get("citizenship_required")

        # If context has no explicit citizenship requirement -> PASS
        if not required and not meta_cit:
            return RuleResult(
                rule_name="citizenship_eligibility",
                decision=RuleDecision.PASS,
                reason="No citizenship restriction detected.",
            )

        cand_cit = self._get_attr(eligibility, ["citizenship", "country_of_citizenship"])
        if cand_cit is None:
            return RuleResult(
                rule_name="citizenship_eligibility",
                decision=RuleDecision.UNKNOWN,
                reason="Candidate citizenship status is missing.",
                field="citizenship",
            )

        target_cit = str(required or meta_cit).lower()
        if target_cit in str(cand_cit).lower():
            return RuleResult(
                rule_name="citizenship_eligibility",
                decision=RuleDecision.PASS,
                reason=f"Candidate citizenship '{cand_cit}' satisfies requirement '{target_cit}'.",
            )

        return RuleResult(
            rule_name="citizenship_eligibility",
            decision=RuleDecision.REJECT,
            reason=f"Role requires '{target_cit}' citizenship; candidate citizenship is '{cand_cit}'.",
            field="citizenship",
            job_value=target_cit,
            candidate_value=cand_cit,
        )

    # ── Rule 2: Visa Sponsorship ──

    def check_visa_sponsorship(
        self,
        context: EvaluationContext,
        eligibility: Any,
    ) -> RuleResult:
        """Verify visa sponsorship constraints."""
        visa_avail = context.visa_sponsorship  # "Yes", "No", "Unknown"
        requires_sponsor = self._get_attr(eligibility, ["requires_sponsorship", "visa_sponsorship_needed"])
        visa_status = self._get_attr(eligibility, ["visa_status"])

        if visa_avail != "No":
            return RuleResult(
                rule_name="visa_sponsorship_eligibility",
                decision=RuleDecision.PASS,
                reason="Role offers or does not restrict visa sponsorship.",
            )

        # Job explicitly states NO sponsorship
        if requires_sponsor is None and visa_status is None:
            return RuleResult(
                rule_name="visa_sponsorship_eligibility",
                decision=RuleDecision.UNKNOWN,
                reason="Candidate visa sponsorship requirements missing.",
                field="visa_status",
            )

        needs_visa = False
        if requires_sponsor is True:
            needs_visa = True
        elif visa_status and "require" in str(visa_status).lower():
            needs_visa = True

        if needs_visa:
            return RuleResult(
                rule_name="visa_sponsorship_eligibility",
                decision=RuleDecision.REJECT,
                reason="Role explicitly offers no visa sponsorship; candidate requires sponsorship.",
                field="visa_status",
                job_value="No Sponsorship",
                candidate_value=visa_status or "Requires Sponsorship",
            )

        return RuleResult(
            rule_name="visa_sponsorship_eligibility",
            decision=RuleDecision.PASS,
            reason="Candidate does not require visa sponsorship.",
        )

    # ── Rule 3: Security Clearance ──

    def check_security_clearance(
        self,
        context: EvaluationContext,
        eligibility: Any,
    ) -> RuleResult:
        """Verify security clearance requirements."""
        clearance_req = self._get_attr(context, ["security_clearance_required"]) or context.metadata.get("security_clearance")

        if not clearance_req:
            return RuleResult(
                rule_name="security_clearance_eligibility",
                decision=RuleDecision.PASS,
                reason="No security clearance required.",
            )

        cand_clearance = self._get_attr(eligibility, ["clearance", "security_clearance"])
        if cand_clearance is None:
            return RuleResult(
                rule_name="security_clearance_eligibility",
                decision=RuleDecision.UNKNOWN,
                reason="Candidate security clearance status missing.",
                field="clearance",
            )

        no_clearance = not cand_clearance or str(cand_clearance).lower() in ("none", "false", "")
        if no_clearance:
            return RuleResult(
                rule_name="security_clearance_eligibility",
                decision=RuleDecision.REJECT,
                reason=f"Security clearance '{clearance_req}' required; candidate has no active clearance.",
                field="clearance",
                job_value=clearance_req,
                candidate_value=cand_clearance,
            )

        return RuleResult(
            rule_name="security_clearance_eligibility",
            decision=RuleDecision.PASS,
            reason=f"Candidate clearance '{cand_clearance}' recorded.",
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
