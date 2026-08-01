"""
LearningPlanner — Phase 2 Learning Roadmap Planner

Builds targeted learning roadmaps from semantic graph traversal, recommending the
smallest capability gaps to improve job match eligibility.

Delegates to SemanticReasoner for prerequisite graph discovery and alias resolution.

Responsibilities:
  - Construct ordered LearningMilestones for missing capabilities.
  - Traverse prerequisite graph so foundational skills are learned first.
  - Calculate estimated effort hours and impact score priorities.
  - Zero scoring mutations.

Invariant: Immutable RoadmapPlan output.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.career_intelligence.learning.models import (
    LearningMilestone,
    LearningPath,
    RoadmapPlan,
)
from src.career_intelligence.reasoning.semantic_reasoner import SemanticReasoner

logger = logging.getLogger("LearningPlanner")


class LearningPlanner:
    """Builds structured learning roadmaps from comparison gaps and ontology traversal."""

    def __init__(self, reasoner: SemanticReasoner | None = None) -> None:
        self._reasoner = reasoner or SemanticReasoner()

    def plan_roadmap(
        self,
        comparison_result: Dict[str, Any],
        target_role: str = "Target Position",
    ) -> RoadmapPlan:
        """Generate a complete RoadmapPlan from ComparisonEngine results.

        Args:
            comparison_result: Dict output from ComparisonEngine.compare().
            target_role:       Display target role title.

        Returns:
            Immutable RoadmapPlan.
        """
        cmp_id = comparison_result.get("comparison_id", "cmp_unknown")
        missing_techs = comparison_result.get("missing_techs", [])
        missing_skills = comparison_result.get("missing_skills", [])

        # Build primary learning path
        primary_path = self._build_path(missing_techs, missing_skills, target_role)

        summary = (
            f"Learning roadmap generated for {target_role}: "
            f"{len(primary_path.milestones)} milestones requiring "
            f"~{primary_path.total_estimated_hours} total effort hours "
            f"to bridge capability gaps."
        )

        logger.info(
            "LearningPlanner: generated plan for cmp_id=%s → %d milestones, %d total hours",
            cmp_id,
            len(primary_path.milestones),
            primary_path.total_estimated_hours,
        )

        return RoadmapPlan(
            comparison_id=cmp_id,
            primary_path=primary_path,
            alternative_paths=[],
            summary=summary,
        )

    def _build_path(
        self,
        missing_techs: List[str],
        missing_skills: List[str],
        target_role: str,
    ) -> LearningPath:
        """Build an ordered LearningPath prioritizing prerequisite skills first."""
        milestones: List[LearningMilestone] = []
        added_caps: set[str] = set()

        all_missing = missing_techs + missing_skills

        for raw_cap in all_missing:
            cap_name = self._reasoner.resolve_aliases(raw_cap)
            if cap_name.lower() in added_caps:
                continue

            # 1. Discover prerequisites
            prereqs = self._reasoner.discover_prerequisites(cap_name)

            # Insert any unlearned prerequisite first
            for prereq in prereqs:
                if prereq.lower() not in added_caps:
                    added_caps.add(prereq.lower())
                    milestones.append(
                        LearningMilestone(
                            capability=prereq,
                            category="prerequisite",
                            prerequisites=[],
                            estimated_effort_hours=15,
                            impact_score=0.9,
                            priority="CRITICAL",
                            reasoning=f"Foundational prerequisite required before mastering {cap_name}.",
                        )
                    )

            # 2. Insert main capability milestone
            added_caps.add(cap_name.lower())
            is_tech = raw_cap in missing_techs
            priority_val = "HIGH" if is_tech else "MEDIUM"

            milestones.append(
                LearningMilestone(
                    capability=cap_name,
                    category="technology" if is_tech else "skill",
                    prerequisites=prereqs,
                    estimated_effort_hours=25 if is_tech else 15,
                    impact_score=0.85 if is_tech else 0.7,
                    priority=priority_val,
                    reasoning=f"Direct missing requirement for '{target_role}'.",
                )
            )

        total_hours = sum(m.estimated_effort_hours for m in milestones)
        gain = min(35.0, len(milestones) * 7.5)

        return LearningPath(
            target_role=target_role,
            milestones=milestones,
            total_estimated_hours=total_hours,
            expected_eligibility_gain=round(gain, 1),
        )
