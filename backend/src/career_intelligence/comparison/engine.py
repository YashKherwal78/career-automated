"""
Comparison Engine — Phase 2 Semantic Match & Comparison Orchestrator

ComparisonEngine is the SINGLE public entry point for candidate/job comparison
and scoring. It consumes:
  - EvaluationContext (canonical job representation)
  - CandidateContext (derived candidate representation)
  - CandidatePreferences (optional user preferences)
  - CandidateEligibility (optional user legal status)
  - ScreeningResult (screening outcomes)

Internally, ComparisonEngine coordinates (delegates.py):
  - EvaluationEngine
  - SemanticReasoner
  - ScoreAggregator
  - SnapshotBuilder

Scoring Determinism Invariant:
  ComparisonEngine is fully deterministic for identical inputs.
  Scores come strictly from rule weights — non-deterministic layers are forbidden
  from altering score numbers.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional

from src.career_intelligence.candidate_intelligence.analyzer import CandidateAnalyzer
from src.career_intelligence.candidate_intelligence.models import CandidateContext
from src.career_intelligence.comparison.delegates import (
    EvaluationEngine,
    ScoreAggregator,
    SemanticReasoner,
    SnapshotBuilder,
)
from src.career_intelligence.evaluation.models import EvaluationContext
from src.career_intelligence.evaluation.resolver import EvaluationContextResolver
from src.career_intelligence.job_intelligence.assembler import JobAssembler
from src.career_intelligence.models import (
    CandidateProfile,
    CertificationComparison,
    ComparisonContext,
    ComparisonResult,
    EducationComparison,
    EmploymentComparison,
    ExperienceComparison,
    LanguageComparison,
    LocationComparison,
    ProjectComparison,
    ResponsibilityComparison,
    SkillComparison,
    TechnologyComparison,
)
from src.career_intelligence.screening.models import ScreeningResult
from src.career_intelligence.screening.orchestrator import ScreeningOrchestrator
from src.discovery.jie.models import StructuredJob

logger = logging.getLogger("ComparisonEngine")


class ComparisonEngine:
    """Phase 2 Comparison Engine: Single entry point for semantic match & scoring."""

    def __init__(self) -> None:
        self._eval_engine = EvaluationEngine()
        self._reasoner = SemanticReasoner()
        self._aggregator = ScoreAggregator()
        self._snapshot_builder = SnapshotBuilder()
        self._screening_orchestrator = ScreeningOrchestrator()

    def compare(
        self,
        eval_ctx: EvaluationContext,
        cand_ctx: CandidateContext,
        candidate_profile: Optional[Any] = None,
        candidate_preferences: Optional[Any] = None,
        candidate_eligibility: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Perform semantic candidate-to-job match comparison.

        Args:
            eval_ctx:              Canonical EvaluationContext.
            cand_ctx:              Derived CandidateContext.
            candidate_profile:     Optional raw candidate profile/object.
            candidate_preferences: Optional user preferences object.
            candidate_eligibility: Optional user eligibility object.
        """
        # Fall back to candidate_profile if preferences/eligibility sub-objects not passed
        prefs_target = candidate_preferences if candidate_preferences is not None else (candidate_profile or cand_ctx)
        elig_target = candidate_eligibility if candidate_eligibility is not None else (candidate_profile or cand_ctx)

        # 1. Run Screening Orchestration
        screening_res = self._screening_orchestrator.screen(
            context=eval_ctx,
            candidate_profile=cand_ctx,
            candidate_preferences=prefs_target,
            candidate_eligibility=elig_target,
        )

        # 2. Evaluate Dimensions via internal delegates
        skills_score, matched_skills, missing_skills = self._eval_engine.evaluate_skills(eval_ctx, cand_ctx)
        techs_score, matched_techs, missing_techs = self._eval_engine.evaluate_technologies(eval_ctx, cand_ctx)
        exp_score, gap_years = self._eval_engine.evaluate_experience(eval_ctx, cand_ctx)
        domain_score, matched_domains = self._eval_engine.evaluate_domain(eval_ctx, cand_ctx)

        # 3. Semantic reasoning
        reasoning = self._reasoner.reason_capabilities(eval_ctx, cand_ctx)

        # 4. Aggregate score using policy weights
        weights = eval_ctx.policy.weights
        overall_score, breakdown = self._aggregator.aggregate(
            weights=weights,
            skills_score=skills_score,
            techs_score=techs_score,
            exp_score=exp_score,
            domain_score=domain_score,
            screening_result=screening_res,
        )

        # 5. Generate reproducible snapshot
        comparison_id = f"cmp_{eval_ctx.jd_hash[:8]}_{cand_ctx.inferred_level.value}"
        snapshot = self._snapshot_builder.build_snapshot(
            comparison_id=comparison_id,
            eval_ctx=eval_ctx,
            cand_ctx=cand_ctx,
            overall_score=overall_score,
            breakdown=breakdown,
            screening_result=screening_res,
        )

        logger.info(
            "ComparisonEngine: evaluated jd_hash=%s against cand_level=%s → overall_score=%.2f, screening=%s",
            eval_ctx.jd_hash,
            cand_ctx.inferred_level.value,
            overall_score,
            screening_res.overall,
        )

        return {
            "comparison_id": comparison_id,
            "overall_score": overall_score,
            "screening": screening_res,
            "breakdown": breakdown,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "matched_techs": matched_techs,
            "missing_techs": missing_techs,
            "matched_domains": matched_domains,
            "experience_gap_years": gap_years,
            "reasoning": reasoning,
            "snapshot": snapshot,
        }


# ---------------------------------------------------------------------------
# Backward Compatibility Shim for Phase 1 `CareerComparisonEngine`
# ---------------------------------------------------------------------------

class CareerComparisonEngine:
    """Backward compatibility adapter for Phase 1 calls.

    Wraps the Phase 2 pipeline (JobAssembler -> EvaluationContextResolver ->
    CandidateAnalyzer -> ComparisonEngine) to return legacy `ComparisonResult`.
    """

    def __init__(self) -> None:
        self._assembler = JobAssembler()
        self._resolver = EvaluationContextResolver()
        self._analyzer = CandidateAnalyzer()
        self._engine = ComparisonEngine()

    def compare(self, profile: CandidateProfile, job: StructuredJob) -> ComparisonResult:
        """Executes domain comparisons using Phase 2 engine under the hood."""
        # Convert legacy StructuredJob to EvaluationContext
        structured = self._assembler.process(title=job.title, jd_text=f"{job.title} {' '.join(job.skills)} {' '.join(job.technologies)}")
        eval_ctx = self._resolver.resolve(structured)

        # Derive CandidateContext from CandidateProfile
        cand_ctx = self._analyzer.analyze(profile)

        # Run ComparisonEngine
        res = self._engine.compare(eval_ctx, cand_ctx, candidate_profile=profile)

        # Build legacy ComparisonResult models for callers
        skills_comp = SkillComparison(
            score=res["breakdown"]["skills"] / 100.0,
            matched=res["matched_skills"],
            missing=res["missing_skills"],
        )

        techs_comp = TechnologyComparison(
            score=res["breakdown"]["technologies"] / 100.0,
            matched=res["matched_techs"],
            missing=res["missing_techs"],
        )

        exp_comp = ExperienceComparison(
            score=res["breakdown"]["experience"] / 100.0,
            required_years=job.experience_min or 0,
            candidate_years=cand_ctx.years_experience,
            gap=res["experience_gap_years"],
        )

        now_iso = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        context = ComparisonContext(
            parser_version="2.0.0",
            ontology_version="1.0.0",
            weight_profile=eval_ctx.policy.policy_id,
            comparison_timestamp=now_iso,
            comparison_algorithm_version="3.0.0",
            feature_flags={"phase2_engine": True},
        )

        strengths = []
        weaknesses = []
        if res["overall_score"] >= 75.0:
            strengths.append("Strong overall profile and skill alignment with job policy.")
        if res["missing_techs"]:
            weaknesses.append(f"Missing technologies: {', '.join(res['missing_techs'][:3])}")

        return ComparisonResult(
            candidate_id=getattr(profile, "candidate_id", None),
            job_id=getattr(job, "job_id", None),
            generated_at=now_iso,
            profile_version="2.0.0",
            job_version="2.0.0",
            context=context,
            skills=skills_comp,
            technologies=techs_comp,
            experience=exp_comp,
            education=EducationComparison(score=1.0, fit=True),
            location=LocationComparison(score=1.0, location_fit=True),
            employment=EmploymentComparison(score=1.0, employment_type_fit=True),
            projects=ProjectComparison(score=1.0),
            certifications=CertificationComparison(score=1.0),
            responsibilities=ResponsibilityComparison(score=1.0),
            languages=LanguageComparison(score=1.0),
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=[],
            metadata={"phase2_res": res},
        )
