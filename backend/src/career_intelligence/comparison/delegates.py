"""
Internal Comparison Delegates — Phase 2 Comparison Engine

Internal implementation details for ComparisonEngine. Non-public APIs.

Delegates:
  - EvaluationEngine: Evaluates rules per dimension.
  - SemanticReasoner: Resolves capability / domain adjacency & overlaps.
  - ScoreAggregator: Computes weighted dimensional match scores.
  - SnapshotBuilder: Builds immutable, versioned ComparisonSnapshot.

Invariant: Fully deterministic scoring for identical inputs.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Set, Tuple

from src.career_intelligence.candidate_intelligence.models import CandidateContext
from src.career_intelligence.evaluation.models import EvaluationContext
from src.career_intelligence.models.common import ArtifactVersion, AuditInfo
from src.career_intelligence.models.snapshot import ComparisonSnapshot
from src.career_intelligence.screening.models import ScreeningResult

logger = logging.getLogger("ComparisonDelegates")


class EvaluationEngine:
    """Internal delegate: evaluates dimensional matching rules."""

    def evaluate_skills(
        self,
        eval_ctx: EvaluationContext,
        cand_ctx: CandidateContext,
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate skill & capability match.

        Returns (score, matched_skills, missing_skills).
        """
        job_skills = set(s.lower() for s in eval_ctx.skills)
        cand_skills = set(c.value.lower() for c in cand_ctx.capability_vector)

        if not job_skills:
            return (1.0, [], [])

        matched = [s for s in eval_ctx.skills if s.lower() in cand_skills]
        missing = [s for s in eval_ctx.skills if s.lower() not in cand_skills]

        score = len(matched) / len(job_skills)
        return (round(score, 4), matched, missing)

    def evaluate_technologies(
        self,
        eval_ctx: EvaluationContext,
        cand_ctx: CandidateContext,
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate technology stack match.

        Returns (score, matched_techs, missing_techs).
        """
        job_techs = set(t.lower() for t in eval_ctx.technologies)
        cand_techs = set(c.value.lower() for c in cand_ctx.capability_vector)

        if not job_techs:
            return (1.0, [], [])

        matched = [t for t in eval_ctx.technologies if t.lower() in cand_techs]
        missing = [t for t in eval_ctx.technologies if t.lower() not in cand_techs]

        score = len(matched) / len(job_techs)
        return (round(score, 4), matched, missing)

    def evaluate_experience(
        self,
        eval_ctx: EvaluationContext,
        cand_ctx: CandidateContext,
    ) -> Tuple[float, float]:
        """Evaluate experience years match.

        Returns (score, gap_years).
        """
        req_min = eval_ctx.experience_min
        if req_min is None or req_min == 0:
            return (1.0, 0.0)

        cand_years = cand_ctx.years_experience
        if cand_years >= req_min:
            return (1.0, 0.0)

        gap = float(req_min) - cand_years
        ratio = cand_years / float(req_min)
        return (round(max(0.0, ratio), 4), round(gap, 1))

    def evaluate_domain(
        self,
        eval_ctx: EvaluationContext,
        cand_ctx: CandidateContext,
    ) -> Tuple[float, List[str]]:
        """Evaluate domain overlap.

        Returns (score, matched_domains).
        """
        job_domains = set(d.value for d in eval_ctx.domains)
        cand_domains = set(d.value for d in cand_ctx.primary_domains)

        if not job_domains:
            return (1.0, [])

        matched = list(job_domains.intersection(cand_domains))
        score = len(matched) / len(job_domains)
        return (round(score, 4), matched)


class SemanticReasoner:
    """Internal delegate: calculates adjacency & relationship overlaps."""

    def reason_capabilities(
        self,
        eval_ctx: EvaluationContext,
        cand_ctx: CandidateContext,
    ) -> Dict[str, Any]:
        """Determine capability overlap and adjacency."""
        cand_caps = {c.value.lower(): c.confidence for c in cand_ctx.capability_vector}
        job_caps = [c.value.lower() for c in eval_ctx.capabilities]

        direct_matches = [c for c in job_caps if c in cand_caps]
        coverage = len(direct_matches) / len(job_caps) if job_caps else 1.0

        return {
            "capability_coverage": round(coverage, 4),
            "direct_matches": direct_matches,
            "total_job_capabilities": len(job_caps),
        }


class ScoreAggregator:
    """Internal delegate: aggregates dimensional scores using policy weights."""

    def aggregate(
        self,
        weights: Dict[str, float],
        skills_score: float,
        techs_score: float,
        exp_score: float,
        domain_score: float,
        screening_result: ScreeningResult,
    ) -> Tuple[float, Dict[str, float]]:
        """Compute final weighted score.

        If screening_result is REJECT, overall score is zeroed out or heavily penalized.
        """
        # Dimensional breakdown normalized to 0-100 scale
        breakdown = {
            "skills": round(skills_score * 100, 1),
            "technologies": round(techs_score * 100, 1),
            "experience": round(exp_score * 100, 1),
            "domain": round(domain_score * 100, 1),
        }

        # Calculate weighted sum
        w_skills = weights.get("skills", 0.3)
        w_techs = weights.get("technologies", 0.3)
        w_exp = weights.get("experience", 0.25)
        w_domain = weights.get("domain", 0.15)
        total_weight = w_skills + w_techs + w_exp + w_domain

        if total_weight <= 0:
            total_weight = 1.0

        raw_score = (
            (skills_score * w_skills)
            + (techs_score * w_techs)
            + (exp_score * w_exp)
            + (domain_score * w_domain)
        ) / total_weight

        overall_score = round(raw_score * 100, 2)

        # If screening is REJECT, force score to 0.0
        if screening_result.overall == "REJECT":
            overall_score = 0.0

        return (overall_score, breakdown)


class SnapshotBuilder:
    """Internal delegate: constructs an immutable ComparisonSnapshot."""

    def build_snapshot(
        self,
        comparison_id: str,
        eval_ctx: EvaluationContext,
        cand_ctx: CandidateContext,
        overall_score: float,
        breakdown: Dict[str, float],
        screening_result: ScreeningResult,
    ) -> ComparisonSnapshot:
        """Construct ComparisonSnapshot for historical auditability."""
        now_iso = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        hash_payload = json.dumps(
            {
                "comparison_id": comparison_id,
                "jd_hash": eval_ctx.jd_hash,
                "policy_version": eval_ctx.policy_version,
                "overall_score": overall_score,
                "screening": screening_result.overall,
            },
            sort_keys=True,
        )
        snapshot_hash = hashlib.md5(hash_payload.encode("utf-8")).hexdigest()

        return ComparisonSnapshot(
            snapshot_id=f"snap_{snapshot_hash[:12]}",
            comparison_id=comparison_id,
            candidate_version=cand_ctx.schema_version,
            job_version=eval_ctx.schema_version,
            versions=ArtifactVersion(
                parser="2.0.0",
                ontology="1.0.0",
                policy=eval_ctx.policy_version,
                comparison="2.0.0",
            ),
            audit=AuditInfo(generated_at=now_iso),
            hash_value=snapshot_hash,
            metadata={
                "overall_score": overall_score,
                "breakdown": breakdown,
                "screening_status": screening_result.overall,
                "conflicts_count": len(screening_result.conflicts),
            },
        )
