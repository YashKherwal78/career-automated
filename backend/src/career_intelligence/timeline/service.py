"""
CareerTimelineService — Phase 3 Career Timeline Module

Records historical progression snapshots and computes progress reports over time.

Invariant: Zero modification of comparison scores.
"""

from __future__ import annotations

import datetime
import logging
from typing import Dict, List, Optional

from src.career_intelligence.candidate_intelligence.models import CandidateContext
from src.career_intelligence.timeline.models import (
    CareerTimeline,
    ProgressReport,
    TimelineSnapshot,
)

logger = logging.getLogger("CareerTimelineService")


class CareerTimelineService:
    """Manages candidate progression history."""

    def __init__(self) -> None:
        self._timelines: Dict[str, List[TimelineSnapshot]] = {}

    def record_snapshot(
        self,
        candidate_id: str,
        cand_ctx: CandidateContext,
        avg_score: float,
        unlocked_count: int,
    ) -> TimelineSnapshot:
        """Record a historical progression snapshot."""
        now_iso = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        snap = TimelineSnapshot(
            snapshot_id=f"tl_{candidate_id}_{len(self._timelines.get(candidate_id, [])) + 1}",
            recorded_at=now_iso,
            inferred_seniority=cand_ctx.inferred_level.value,
            capability_count=len(cand_ctx.capability_vector),
            avg_match_score=avg_score,
            unlocked_opportunities_count=unlocked_count,
        )

        if candidate_id not in self._timelines:
            self._timelines[candidate_id] = []
        self._timelines[candidate_id].append(snap)

        logger.info("CareerTimelineService: recorded snapshot %s for candidate %s", snap.snapshot_id, candidate_id)
        return snap

    def generate_progress_report(
        self,
        candidate_id: str,
        new_skills: Optional[List[str]] = None,
    ) -> ProgressReport:
        """Generate progress report from historical snapshots."""
        history = self._timelines.get(candidate_id, [])
        if len(history) < 2:
            first = history[0] if history else None
            score_delta = 0.0
            unlocked_new = 0
        else:
            first = history[0]
            last = history[-1]
            score_delta = round(last.avg_match_score - first.avg_match_score, 2)
            unlocked_new = max(0, last.unlocked_opportunities_count - first.unlocked_opportunities_count)

        learned = new_skills or []
        summary = (
            f"Progress Report for '{candidate_id}': Match score improved by {score_delta:+.1f} points. "
            f"Unlocked {unlocked_new} new opportunities and mastered {len(learned)} new capabilities."
        )

        return ProgressReport(
            candidate_id=candidate_id,
            timespan_days=30,
            score_delta=score_delta,
            new_capabilities_learned=learned,
            new_opportunities_unlocked=unlocked_new,
            summary=summary,
        )

    def get_timeline(self, candidate_id: str) -> CareerTimeline:
        """Fetch complete timeline for candidate."""
        history = self._timelines.get(candidate_id, [])
        return CareerTimeline(
            candidate_id=candidate_id,
            history=history,
            milestones_achieved=[f"Recorded {len(history)} progression checkpoints."],
        )
