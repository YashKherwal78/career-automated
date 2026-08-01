"""
FeedbackLearningEngine — Phase 3 Feedback Learning Engine

Consumes real application outcome events (interview, offer, rejection, OA) to refine
RankingPolicy weights over time.

Invariant: Never modifies comparison match scores.
"""

from __future__ import annotations

import datetime
import logging
from typing import Dict, List

from src.career_intelligence.feedback.models import FeedbackEvent, PolicyAdjustment
from src.career_intelligence.ranking.models import RankingPolicy

logger = logging.getLogger("FeedbackLearningEngine")


class FeedbackLearningEngine:
    """Refines ranking policies using empirical outcome events."""

    def __init__(self) -> None:
        self._events: List[FeedbackEvent] = []

    def log_event(
        self,
        candidate_id: str,
        job_id: str,
        outcome: str,
        matched_score: float,
    ) -> FeedbackEvent:
        """Log an empirical feedback event."""
        now_iso = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        evt = FeedbackEvent(
            event_id=f"evt_{len(self._events) + 1}",
            candidate_id=candidate_id,
            job_id=job_id,
            outcome=outcome,
            matched_score=matched_score,
            recorded_at=now_iso,
        )
        self._events.append(evt)

        logger.info("FeedbackLearningEngine: logged feedback event %s outcome=%s", evt.event_id, outcome)
        return evt

    def optimize_ranking_policy(self, current_policy: RankingPolicy) -> Tuple[RankingPolicy, PolicyAdjustment]:
        """Refine ranking policy weights based on historical feedback events using outcome weighting.

        Outcome weights:
          - OFFER: +1.0
          - INTERVIEW / RECRUITER_RESPONSE: +0.5
          - OA: +0.2
          - REJECTED: -0.3

        Returns updated RankingPolicy and PolicyAdjustment record.
        """
        if not self._events:
            adj = PolicyAdjustment(
                policy_id=current_policy.policy_id,
                previous_response_weight=current_policy.response_likelihood_weight,
                adjusted_response_weight=current_policy.response_likelihood_weight,
                adjustment_reason="No feedback events recorded; policy weight unchanged.",
            )
            return (current_policy, adj)

        outcome_signal = 0.0
        for evt in self._events:
            if evt.outcome == "OFFER":
                outcome_signal += 1.0
            elif evt.outcome in ("INTERVIEW", "RECRUITER_RESPONSE"):
                outcome_signal += 0.5
            elif evt.outcome == "OA":
                outcome_signal += 0.2
            elif evt.outcome == "REJECTED":
                outcome_signal -= 0.3

        avg_signal = outcome_signal / float(len(self._events))
        learning_rate = 0.05
        prev_w = current_policy.response_likelihood_weight

        # Gradient step with bounds [0.05, 0.35]
        new_w = max(0.05, min(0.35, round(prev_w + (learning_rate * avg_signal), 3)))

        # Increment policy version
        v_parts = current_policy.policy_id.split("_v")
        base_id = v_parts[0] if len(v_parts) > 1 else current_policy.policy_id
        curr_ver = int(v_parts[1]) if len(v_parts) > 1 and v_parts[1].isdigit() else 1
        new_policy_id = f"{base_id}_v{curr_ver + 1}"

        adjusted_policy = current_policy.model_copy(
            update={
                "policy_id": new_policy_id,
                "response_likelihood_weight": new_w,
            }
        )

        reason = (
            f"Evaluated {len(self._events)} events (avg outcome signal={avg_signal:+.2f}). "
            f"Gradient step adjusted response weight from {prev_w:.3f} to {new_w:.3f} under policy {new_policy_id}."
        )

        adj = PolicyAdjustment(
            policy_id=new_policy_id,
            previous_response_weight=prev_w,
            adjusted_response_weight=new_w,
            adjustment_reason=reason,
        )

        logger.info("FeedbackLearningEngine: %s", reason)
        return (adjusted_policy, adj)
