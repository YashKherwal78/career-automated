"""
OpportunityRanker — Phase 3 Opportunity Ranking Engine

Ranks job opportunities deterministically by combining comparison match scores,
company quality, response likelihood, compensation alignment, and job freshness.

Invariant: Never modifies comparison match score.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
from typing import Any, Dict, List, Optional

from src.career_intelligence.ranking.models import (
    RankedOpportunity,
    RankingFactor,
    RankingPolicy,
    RankingSnapshot,
)

logger = logging.getLogger("OpportunityRanker")


class OpportunityRanker:
    """Ranks opportunities deterministically."""

    def __init__(self, policy: RankingPolicy | None = None) -> None:
        self._policy = policy or RankingPolicy()

    def rank_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
    ) -> RankingSnapshot:
        """Rank a list of comparison result opportunities.

        Args:
            opportunities: List of dicts containing:
              - opportunity_id (str)
              - job_title (str)
              - company_name (str)
              - comparison_result (dict from ComparisonEngine)
              - company_quality (float 0-1, optional)
              - response_likelihood (float 0-1, optional)
              - compensation_score (float 0-1, optional)
              - freshness_days (int, optional)

        Returns:
            RankingSnapshot containing ordered RankedOpportunity items.
        """
        ranked_list: List[RankedOpportunity] = []

        for opp in opportunities:
            opp_id = opp.get("opportunity_id", "opp_unknown")
            title = opp.get("job_title", "Unknown Role")
            company = opp.get("company_name", "Unknown Company")
            comp_res = opp.get("comparison_result", {})

            match_score = float(comp_res.get("overall_score", 0.0))
            screening_status = getattr(comp_res.get("screening"), "overall", "PASS")

            comp_quality = float(opp.get("company_quality", 0.8))
            resp_likelihood = float(opp.get("response_likelihood", 0.75))
            comp_align = float(opp.get("compensation_score", 0.8))
            freshness_days = int(opp.get("freshness_days", 1))

            # Freshness score (1.0 for <=2 days, scaling down to 0.2 for >30 days)
            freshness_score = max(0.2, min(1.0, 1.0 - (freshness_days / 30.0)))

            # Calculate factor scores
            factors = [
                RankingFactor(
                    name="match_score",
                    weight=self._policy.match_score_weight,
                    raw_value=match_score / 100.0,
                    weighted_score=(match_score / 100.0) * self._policy.match_score_weight,
                    explanation=f"Comparison match score is {match_score:.1f}/100.",
                ),
                RankingFactor(
                    name="company_quality",
                    weight=self._policy.company_quality_weight,
                    raw_value=comp_quality,
                    weighted_score=comp_quality * self._policy.company_quality_weight,
                    explanation=f"Company quality score is {comp_quality * 100:.0f}%.",
                ),
                RankingFactor(
                    name="response_likelihood",
                    weight=self._policy.response_likelihood_weight,
                    raw_value=resp_likelihood,
                    weighted_score=resp_likelihood * self._policy.response_likelihood_weight,
                    explanation=f"Historical response likelihood is {resp_likelihood * 100:.0f}%.",
                ),
                RankingFactor(
                    name="compensation",
                    weight=self._policy.compensation_weight,
                    raw_value=comp_align,
                    weighted_score=comp_align * self._policy.compensation_weight,
                    explanation=f"Compensation alignment score is {comp_align * 100:.0f}%.",
                ),
                RankingFactor(
                    name="freshness",
                    weight=self._policy.freshness_weight,
                    raw_value=freshness_score,
                    weighted_score=freshness_score * self._policy.freshness_weight,
                    explanation=f"Job posted {freshness_days} days ago.",
                ),
            ]

            raw_opp_score = sum(f.weighted_score for f in factors)
            opp_score = round(raw_opp_score * 100.0, 2)

            # If screening rejected, force opp_score = 0.0
            if screening_status == "REJECT":
                opp_score = 0.0

            explanation = (
                f"Opportunity score {opp_score:.1f} calculated from match score ({match_score:.1f}), "
                f"company quality ({comp_quality * 100:.0f}%), and response likelihood ({resp_likelihood * 100:.0f}%)."
            )

            ranked_list.append(
                RankedOpportunity(
                    rank=0,  # Assigned after sorting
                    opportunity_id=opp_id,
                    job_title=title,
                    company_name=company,
                    comparison_match_score=match_score,
                    opportunity_score=opp_score,
                    explanation=explanation,
                    factors=factors,
                )
            )

        # Sort by opportunity_score descending
        ranked_list.sort(key=lambda r: r.opportunity_score, reverse=True)

        # Re-assign 1-based ranks
        final_rankings: List[RankedOpportunity] = []
        for idx, item in enumerate(ranked_list, start=1):
            final_rankings.append(item.model_copy(update={"rank": idx}))

        now_iso = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        snap_id = f"rnk_{hashlib.md5(now_iso.encode('utf-8')).hexdigest()[:10]}"

        logger.info(
            "OpportunityRanker: ranked %d opportunities under policy %s",
            len(final_rankings),
            self._policy.policy_id,
        )

        return RankingSnapshot(
            snapshot_id=snap_id,
            generated_at=now_iso,
            policy_id=self._policy.policy_id,
            total_opportunities_ranked=len(final_rankings),
            rankings=final_rankings,
        )
