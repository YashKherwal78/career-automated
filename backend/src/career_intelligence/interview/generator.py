"""
InterviewIntelligenceGenerator — Phase 3 Interview Intelligence

Generates targeted interview preparation plans from EvidenceReport and RoadmapPlan.

Invariant: Zero modification of match scores.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from src.career_intelligence.explainability.models import (
    EvidenceReport,
    InterviewQuestion,
)
from src.career_intelligence.interview.models import (
    ConceptWeakness,
    InterviewPreparationPlan,
    QuestionBank,
)

from src.career_intelligence.reasoning.semantic_reasoner import SemanticReasoner

logger = logging.getLogger("InterviewIntelligenceGenerator")


class InterviewIntelligenceGenerator:
    """Generates interview preparation plans."""

    def generate_plan(
        self,
        evidence_report: EvidenceReport,
        job_title: str = "Target Position",
        roadmap_plan: Any | None = None,
        reasoner: SemanticReasoner | None = None,
    ) -> InterviewPreparationPlan:
        """Generate an InterviewPreparationPlan integrating roadmap and semantic graph data.

        Args:
            evidence_report: EvidenceReport from EvidenceBuilder.
            job_title:       Target job title.
            roadmap_plan:    Optional RoadmapPlan from LearningPlanner.
            reasoner:        Optional SemanticReasoner instance.

        Returns:
            Immutable InterviewPreparationPlan.
        """
        score = evidence_report.overall_score
        readiness = max(20.0, min(100.0, score * 1.05))

        # 1. Build Question Bank with prerequisite awareness
        phone_questions: List[InterviewQuestion] = []
        tech_questions: List[InterviewQuestion] = []
        design_questions: List[InterviewQuestion] = []

        # If roadmap_plan exists, inspect milestones for prerequisite questions
        milestones = []
        if roadmap_plan and hasattr(roadmap_plan, "primary_path"):
            milestones = getattr(roadmap_plan.primary_path, "milestones", [])

        for m in milestones[:3]:
            cap = getattr(m, "capability", "")
            cat = getattr(m, "category", "")
            prereqs = getattr(m, "prerequisites", [])

            if cat == "prerequisite":
                phone_questions.append(
                    InterviewQuestion(
                        topic=cap,
                        question=f"Since {cap} is a foundational requirement, how experienced are you with its core concepts?",
                        focus_area="technical_depth",
                        difficulty="medium",
                    )
                )
            else:
                tech_questions.append(
                    InterviewQuestion(
                        topic=cap,
                        question=f"How would you apply {cap} in production, and what architectural trade-offs have you managed?",
                        focus_area="technical_depth",
                        difficulty="hard" if not prereqs else "medium",
                    )
                )

        # Fallback if no roadmap milestones passed
        if not tech_questions:
            for item in evidence_report.missing_capabilities[:3]:
                cap = item.title.replace("Missing Technology: ", "").replace("Missing Skill: ", "")
                tech_questions.append(
                    InterviewQuestion(
                        topic=cap,
                        question=f"How would you integrate {cap} into a production service, and what trade-offs would you consider?",
                        focus_area="technical_depth",
                        difficulty="hard",
                    )
                )

        phone_questions.append(
            InterviewQuestion(
                topic="Background Verification",
                question=f"Walk me through your experience relevant to the '{job_title}' role.",
                focus_area="experience_verification",
                difficulty="medium",
            )
        )

        design_questions.append(
            InterviewQuestion(
                topic="System Design",
                question="Design a high-throughput, fault-tolerant distributed logging service.",
                focus_area="technical_depth",
                difficulty="hard",
            )
        )

        q_bank = QuestionBank(
            phone_screen_questions=phone_questions,
            technical_deep_dive_questions=tech_questions,
            system_design_questions=design_questions,
        )

        # 2. Build Concept Weaknesses
        weaknesses: List[ConceptWeakness] = []
        for w in evidence_report.weaknesses[:3]:
            weaknesses.append(
                ConceptWeakness(
                    concept_name=w.title,
                    severity="HIGH" if "Gap" in w.title else "MEDIUM",
                    recommended_study_hours=6,
                    key_topics=[f"Core mechanics of {w.title}", "Production best practices"],
                )
            )

        summary = (
            f"Interview Readiness Confidence: {readiness:.1f}%. "
            f"Generated {len(tech_questions) + len(phone_questions) + len(design_questions)} interview questions "
            f"and {len(weaknesses)} concept study areas."
        )

        logger.info("InterviewIntelligenceGenerator: generated plan for cmp_id=%s", evidence_report.comparison_id)

        return InterviewPreparationPlan(
            comparison_id=evidence_report.comparison_id,
            job_title=job_title,
            readiness_confidence=round(readiness, 1),
            question_bank=q_bank,
            concept_weaknesses=weaknesses,
            study_roadmap_summary=summary,
        )
