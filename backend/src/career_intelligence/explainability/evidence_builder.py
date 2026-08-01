"""
EvidenceBuilder — Phase 2 Explainability Layer

Generates structured EvidenceReport from comparison outputs and ComparisonSnapshot.

Responsibilities:
  - Explain WHY scores were assigned.
  - Categorize strengths, weaknesses, missing capabilities, positive semantic matches,
    and screening observations.
  - Absolutely NEVER recompute or modify scores.

Invariant: Immutable EvidenceReport generation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.career_intelligence.explainability.models import (
    EvidenceItem,
    EvidenceReport,
)

logger = logging.getLogger("EvidenceBuilder")


class EvidenceBuilder:
    """Generates structured evidence reports from comparison engine results."""

    def build_report(self, comparison_result: Dict[str, Any]) -> EvidenceReport:
        """Build an EvidenceReport from ComparisonEngine output dictionary.

        Args:
            comparison_result: Dictionary returned by ComparisonEngine.compare().

        Returns:
            Immutable EvidenceReport.
        """
        comparison_id = comparison_result.get("comparison_id", "cmp_unknown")
        overall_score = float(comparison_result.get("overall_score", 0.0))
        screening = comparison_result.get("screening")
        screening_status = getattr(screening, "overall", "PASS") if screening else "PASS"

        snapshot = comparison_result.get("snapshot")
        snapshot_id = getattr(snapshot, "snapshot_id", "snap_unknown")

        strengths: List[EvidenceItem] = []
        weaknesses: List[EvidenceItem] = []
        missing_capabilities: List[EvidenceItem] = []
        positive_semantic_matches: List[EvidenceItem] = []
        screening_observations: List[EvidenceItem] = []

        # 1. Process Matched Skills & Technologies (Positive Semantic Matches & Strengths)
        matched_skills = comparison_result.get("matched_skills", [])
        for skill in matched_skills:
            item = EvidenceItem(
                category="positive_semantic_match",
                title=f"Matched Skill: {skill}",
                description=f"Candidate profile demonstrates verified capability in '{skill}'.",
                source_field="skills",
                weight=1.0,
                confidence=0.95,
            )
            positive_semantic_matches.append(item)
            if len(strengths) < 4:
                strengths.append(
                    EvidenceItem(
                        category="strength",
                        title=f"Core Skill Alignment: {skill}",
                        description=f"Direct match found for required skill '{skill}'.",
                        source_field="skills",
                    )
                )

        matched_techs = comparison_result.get("matched_techs", [])
        for tech in matched_techs:
            item = EvidenceItem(
                category="positive_semantic_match",
                title=f"Matched Technology: {tech}",
                description=f"Candidate technology stack includes '{tech}'.",
                source_field="technologies",
                weight=1.0,
                confidence=0.95,
            )
            positive_semantic_matches.append(item)

        # 2. Process Missing Skills & Technologies (Missing Capabilities & Weaknesses)
        missing_techs = comparison_result.get("missing_techs", [])
        for tech in missing_techs:
            item = EvidenceItem(
                category="missing_capability",
                title=f"Missing Technology: {tech}",
                description=f"Job requires technology '{tech}', which is not currently highlighted in candidate profile.",
                source_field="technologies",
                weight=1.0,
                confidence=0.9,
            )
            missing_capabilities.append(item)
            weaknesses.append(
                EvidenceItem(
                    category="weakness",
                    title=f"Tech Stack Gap: {tech}",
                    description=f"Candidate profile lacks explicit evidence for '{tech}'.",
                    source_field="technologies",
                )
            )

        missing_skills = comparison_result.get("missing_skills", [])
        for skill in missing_skills:
            item = EvidenceItem(
                category="missing_capability",
                title=f"Missing Skill: {skill}",
                description=f"Job requires skill '{skill}'.",
                source_field="skills",
                weight=0.8,
                confidence=0.85,
            )
            missing_capabilities.append(item)

        # 3. Experience Gap Analysis
        exp_gap = float(comparison_result.get("experience_gap_years", 0.0))
        if exp_gap > 0.0:
            weaknesses.append(
                EvidenceItem(
                    category="weakness",
                    title=f"Experience Gap ({exp_gap} yrs)",
                    description=f"Candidate has an experience deficit of {exp_gap} years relative to job minimum requirement.",
                    source_field="experience_min",
                )
            )
        else:
            strengths.append(
                EvidenceItem(
                    category="strength",
                    title="Sufficient Experience",
                    description="Candidate meets or exceeds minimum required years of experience.",
                    source_field="years_experience",
                )
            )

        # 4. Process Screening Observations
        if screening:
            matched_rules = getattr(screening, "matched", [])
            for r in matched_rules:
                screening_observations.append(
                    EvidenceItem(
                        category="screening_observation",
                        title=f"Screening Passed: {r}",
                        description=f"Constraint check '{r}' satisfied.",
                        source_field="screening",
                    )
                )

            conflicts = getattr(screening, "conflicts", [])
            for c in conflicts:
                screening_observations.append(
                    EvidenceItem(
                        category="screening_observation",
                        title="Screening Conflict",
                        description=c,
                        source_field="screening",
                        weight=0.0,
                    )
                )

            unknown_list = getattr(screening, "unknown", [])
            for u in unknown_list:
                f_name = getattr(u, "field", "unknown_field")
                r_reason = getattr(u, "reason", "Missing field")
                screening_observations.append(
                    EvidenceItem(
                        category="screening_observation",
                        title=f"Missing Information: {f_name}",
                        description=r_reason,
                        source_field=f_name,
                    )
                )

        logger.info(
            "EvidenceBuilder: generated report for cmp_id=%s → %d strengths, %d weaknesses, %d missing caps",
            comparison_id,
            len(strengths),
            len(weaknesses),
            len(missing_capabilities),
        )

        return EvidenceReport(
            comparison_id=comparison_id,
            snapshot_id=snapshot_id,
            overall_score=overall_score,
            screening_status=screening_status,
            strengths=strengths,
            weaknesses=weaknesses,
            missing_capabilities=missing_capabilities,
            positive_semantic_matches=positive_semantic_matches,
            screening_observations=screening_observations,
            metadata={
                "breakdown": comparison_result.get("breakdown", {}),
                "matched_domains": comparison_result.get("matched_domains", []),
            },
        )
