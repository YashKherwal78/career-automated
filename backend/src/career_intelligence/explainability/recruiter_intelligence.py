"""
RecruiterIntelligence — Phase 2 Recruiter Synthesis Layer

Produces recruiter-facing summaries, candidate risk profiles, and targeted interview
questions derived entirely from deterministic comparison evidence reports.

Responsibilities:
  - Synthesize executive summary, top strengths, primary concerns.
  - Recommend hiring action: STRONG_HIRE, HIRE, CONSIDER, DO_NOT_ADVANCE.
  - Generate targeted interview focus areas.
  - Absolutely NEVER modify underlying mathematical scores.

Invariant: Immutable RecruiterSummary output.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal

from src.career_intelligence.explainability.evidence_builder import EvidenceBuilder
from src.career_intelligence.explainability.models import (
    EvidenceReport,
    InterviewQuestion,
    RecruiterSummary,
)

logger = logging.getLogger("RecruiterIntelligence")


class RecruiterIntelligence:
    """Synthesizes recruiter intelligence reports from evidence data."""

    def __init__(self) -> None:
        self._evidence_builder = EvidenceBuilder()

    def generate_summary(
        self,
        comparison_result: Dict[str, Any],
        job_title: str = "Target Position",
    ) -> RecruiterSummary:
        """Generate a RecruiterSummary from ComparisonEngine output dictionary.

        Args:
            comparison_result: Result dict from ComparisonEngine.compare().
            job_title:         Display job title.

        Returns:
            Immutable RecruiterSummary.
        """
        report = self._evidence_builder.build_report(comparison_result)
        return self.synthesize_from_report(report, job_title=job_title)

    def synthesize_from_report(
        self,
        report: EvidenceReport,
        job_title: str = "Target Position",
    ) -> RecruiterSummary:
        """Synthesize RecruiterSummary directly from an EvidenceReport.

        Args:
            report:    An EvidenceReport from EvidenceBuilder.
            job_title: Display title.

        Returns:
            Immutable RecruiterSummary.
        """
        score = report.overall_score
        status = report.screening_status

        # 1. Determine Recommendation deterministically
        recommendation: Literal["STRONG_HIRE", "HIRE", "CONSIDER", "DO_NOT_ADVANCE"]
        if status == "REJECT" or score < 40.0:
            recommendation = "DO_NOT_ADVANCE"
        elif score >= 80.0:
            recommendation = "STRONG_HIRE"
        elif score >= 65.0:
            recommendation = "HIRE"
        else:
            recommendation = "CONSIDER"

        # 2. Extract Top Strengths
        strengths = [s.title for s in report.strengths[:4]]
        if not strengths:
            strengths = ["Candidate profile meets minimum baseline requirements."]

        # 3. Extract Primary Concerns
        concerns = [w.title for w in report.weaknesses[:4]]
        if status == "REJECT":
            concerns.insert(0, "Failed mandatory candidate screening constraints.")

        # 4. Generate Executive Summary
        exec_summary = (
            f"Candidate evaluated for '{job_title}' achieved a match score of {score:.1f}/100 "
            f"with screening status '{status}'. Recommendation: {recommendation.replace('_', ' ')}. "
            f"Key alignment in {len(report.positive_semantic_matches)} verified capability areas."
        )

        # 5. Generate Targeted Interview Questions
        questions: List[InterviewQuestion] = []
        for missing in report.missing_capabilities[:3]:
            cap_name = missing.title.replace("Missing Technology: ", "").replace("Missing Skill: ", "")
            questions.append(
                InterviewQuestion(
                    topic=cap_name,
                    question=f"Can you describe your practical experience with {cap_name} and how you would apply it in this role?",
                    focus_area="technical_depth",
                    difficulty="medium",
                )
            )

        if not questions:
            questions.append(
                InterviewQuestion(
                    topic="Architecture & System Design",
                    question="Walk us through the architecture of a complex production system you recently designed.",
                    focus_area="technical_depth",
                    difficulty="hard",
                )
            )

        logger.info(
            "RecruiterIntelligence: generated summary for cmp_id=%s → recommendation=%s",
            report.comparison_id,
            recommendation,
        )

        return RecruiterSummary(
            comparison_id=report.comparison_id,
            job_title=job_title,
            overall_recommendation=recommendation,
            overall_score=score,
            executive_summary=exec_summary,
            top_strengths=strengths,
            primary_concerns=concerns,
            interview_focus_areas=questions,
        )
