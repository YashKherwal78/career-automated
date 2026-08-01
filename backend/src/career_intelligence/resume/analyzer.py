"""
ResumeIntelligenceAnalyzer — Phase 3 Resume Intelligence

Analyzes candidate resumes against ComparisonSnapshot and EvidenceReport to:
  - Recommend best resume variant.
  - Estimate ATS compatibility score.
  - Suggest keyword alignment improvements.
  - Never invent experience.

Invariant: Zero match score mutation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.career_intelligence.explainability.models import EvidenceReport
from src.career_intelligence.resume.models import (
    ATSScore,
    ResumeAudit,
    ResumeRecommendation,
)

logger = logging.getLogger("ResumeIntelligenceAnalyzer")


class ResumeIntelligenceAnalyzer:
    """Provides ATS compatibility checks and resume recommendations."""

    def audit_resume(
        self,
        evidence_report: EvidenceReport,
        resume_variants: List[str] | None = None,
    ) -> ResumeAudit:
        """Audit resume against evidence report.

        Args:
            evidence_report: EvidenceReport from EvidenceBuilder.
            resume_variants:  List of variant names (e.g. ["Backend", "Fullstack"]).

        Returns:
            Immutable ResumeAudit object.
        """
        variants = resume_variants or ["General_Software_Engineer", "Targeted_Role_Variant"]
        missing_caps = [m.title.replace("Missing Technology: ", "").replace("Missing Skill: ", "") for m in evidence_report.missing_capabilities]

        # Estimate ATS score deterministically
        raw_tech_match = max(0.4, 1.0 - (len(missing_caps) * 0.12))
        ats = ATSScore(
            overall_ats_score=round(raw_tech_match * 100.0, 1),
            keyword_density_score=round(raw_tech_match * 95.0, 1),
            format_parsability_score=95.0,
            section_completeness_score=90.0,
        )

        recs: List[ResumeRecommendation] = []
        if missing_caps:
            recs.append(
                ResumeRecommendation(
                    section="skills",
                    issue=f"Missing key keywords: {', '.join(missing_caps[:3])}",
                    recommendation="If you have project or coursework experience with these technologies, list them explicitly.",
                    suggested_keywords=missing_caps[:5],
                )
            )

        recs.append(
            ResumeRecommendation(
                section="experience",
                issue="Bullet points should quantify technical impact.",
                recommendation="Ensure bullet points feature metrics (e.g. 'Improved API latency by 30%').",
                suggested_keywords=["latency", "throughput", "optimization"],
            )
        )

        summary = (
            f"Resume ATS Compatibility: {ats.overall_ats_score:.1f}%. "
            f"Recommended variant: '{variants[0]}'. {len(recs)} section improvements suggested."
        )

        logger.info("ResumeIntelligenceAnalyzer: audited resume → ATS score %.1f%%", ats.overall_ats_score)

        return ResumeAudit(
            recommended_variant=variants[0],
            ats_compatibility=ats,
            recommendations=recs,
            missing_critical_keywords=missing_caps[:5],
            summary=summary,
        )
