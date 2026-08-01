"""
CareerStrategyEngine — Phase 3 Strategy Engine

Generates tactical career strategy recommendations derived from ranking snapshots,
roadmap plans, and candidate context.

Invariant: Never modifies comparison scores.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.career_intelligence.ranking.models import RankingSnapshot
from src.career_intelligence.strategy.models import CareerStrategy, StrategicAction

logger = logging.getLogger("CareerStrategyEngine")


class CareerStrategyEngine:
    """Generates high-level career strategy guidance."""

    def generate_strategy(
        self,
        candidate_id: str,
        ranking_snapshot: RankingSnapshot,
        roadmap_plan: Any | None = None,
        candidate_level: str = "mid",
    ) -> CareerStrategy:
        """Generate tactical career strategy plan.

        Args:
            candidate_id:     Candidate identifier.
            ranking_snapshot: RankingSnapshot from OpportunityRanker.
            roadmap_plan:     Optional RoadmapPlan from LearningPlanner.
            candidate_level:  Inferred level ("junior", "mid", "senior", "staff").

        Returns:
            Immutable CareerStrategy object.
        """
        actions: List[StrategicAction] = []

        # 1. Immediate Daily Application Targets
        top_opps = ranking_snapshot.rankings[:10]
        top_companies = [f"{o.job_title} at {o.company_name}" for o in top_opps]

        actions.append(
            StrategicAction(
                category="DAILY_TARGET",
                headline=f"Apply to top {len(top_companies)} matched opportunities today",
                rationale="These roles exhibit high match alignment and strong hiring probability.",
                target_items=top_companies,
                priority="HIGH",
            )
        )

        # 2. Skill Learning Recommendations
        if roadmap_plan and hasattr(roadmap_plan, "primary_path"):
            path = roadmap_plan.primary_path
            top_milestones = [m.capability for m in getattr(path, "milestones", [])[:3]]
            if top_milestones:
                actions.append(
                    StrategicAction(
                        category="SKILL_FOCUS",
                        headline=f"Prioritize learning {', '.join(top_milestones[:2])} over the next two weeks",
                        rationale=f"Acquiring these capabilities is estimated to increase job eligibility by +{getattr(path, 'expected_eligibility_gain', 15.0):.1f}%.",
                        target_items=top_milestones,
                        priority="HIGH",
                    )
                )

        # 3. Company Stage Strategy based on candidate level
        if candidate_level in ("junior", "intern"):
            actions.append(
                StrategicAction(
                    category="COMPANY_TARGETING",
                    headline="Focus on Series A-C startups and high-growth scaleups this month",
                    rationale="Early-career roles at growth-stage startups offer higher interview callback rates and broader scope.",
                    target_items=["Series A Startups", "Series B Startups", "Mid-stage Scaleups"],
                    priority="MEDIUM",
                )
            )
        elif candidate_level in ("senior", "staff"):
            actions.append(
                StrategicAction(
                    category="COMPANY_TARGETING",
                    headline="Target Senior/Staff positions at Tier-1 tech and enterprise platforms",
                    rationale="Your experience level qualifies for high-leverage technical leadership roles.",
                    target_items=["Enterprise Platforms", "Tier-1 Tech Companies"],
                    priority="HIGH",
                )
            )

        summary = (
            f"Strategy for candidate '{candidate_id}': Execute {len(actions)} tactical actions. "
            f"Target {len(top_companies)} daily applications with focus on level '{candidate_level}' roles."
        )

        logger.info("CareerStrategyEngine: generated strategy for %s with %d actions", candidate_id, len(actions))

        return CareerStrategy(
            candidate_id=candidate_id,
            strategy_summary=summary,
            actions=actions,
            daily_application_goal=len(top_companies),
            current_focus_domain=candidate_level,
        )
