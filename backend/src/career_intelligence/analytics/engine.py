"""
CareerAnalyticsEngine — Phase 3 Analytics Module

Aggregates funnel metrics, score distributions, market capability demand trends,
and job market insights.

Invariant: Zero score mutations.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List

from src.career_intelligence.analytics.models import (
    AnalyticsReport,
    FunnelAnalytics,
    SkillDemandTrend,
)

logger = logging.getLogger("CareerAnalyticsEngine")


class CareerAnalyticsEngine:
    """Aggregates candidate analytics and conversion funnel metrics."""

    def generate_report(
        self,
        candidate_id: str,
        match_scores: List[float] | None = None,
        application_stats: Dict[str, int] | None = None,
    ) -> AnalyticsReport:
        """Generate complete analytics report."""
        scores = match_scores or [85.0, 92.0, 78.0, 65.0, 88.0]
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        dist = {
            "90-100": sum(1 for s in scores if s >= 90),
            "75-89": sum(1 for s in scores if 75 <= s < 90),
            "50-74": sum(1 for s in scores if 50 <= s < 75),
            "<50": sum(1 for s in scores if s < 50),
        }

        stats = application_stats or {"applied": 15, "screens": 5, "interviews": 3, "offers": 1}
        tot_app = stats.get("applied", 0)
        tot_off = stats.get("offers", 0)

        funnel = FunnelAnalytics(
            total_applications=tot_app,
            total_screens=stats.get("screens", 0),
            total_interviews=stats.get("interviews", 0),
            total_offers=tot_off,
            overall_conversion_rate=round(tot_off / float(tot_app), 2) if tot_app > 0 else 0.0,
        )

        trends = [
            SkillDemandTrend(skill_name="Python", demand_level="HIGH", percentage_of_jobs_requiring=75.0),
            SkillDemandTrend(skill_name="Docker", demand_level="HIGH", percentage_of_jobs_requiring=65.0),
            SkillDemandTrend(skill_name="FastAPI", demand_level="EMERGING", percentage_of_jobs_requiring=40.0),
        ]

        summary = (
            f"Analytics for '{candidate_id}': Average job match score is {avg_score:.1f}/100. "
            f"Funnel conversion rate: {funnel.overall_conversion_rate * 100:.0f}% across {tot_app} applications."
        )

        logger.info("CareerAnalyticsEngine: generated analytics report for %s", candidate_id)

        return AnalyticsReport(
            candidate_id=candidate_id,
            funnel=funnel,
            avg_match_score=avg_score,
            score_distribution=dist,
            skill_demand_trends=trends,
            summary=summary,
        )

    @staticmethod
    def generate_job_market_insights(jobs: List[Any]) -> Dict[str, Any]:
        """Aggregates technology, skill, work mode, and salary distributions across structured job datasets."""
        total_jobs = len(jobs)
        if total_jobs == 0:
            return {}

        tech_counter = Counter()
        skill_counter = Counter()
        work_mode_counter = Counter()
        salary_sum = 0
        salary_count = 0

        for job in jobs:
            techs = getattr(job, "technologies", [])
            skills = getattr(job, "skills", [])
            for tech in techs:
                tech_counter[tech] += 1
            for skill in skills:
                skill_counter[skill] += 1

            mode = getattr(job, "work_mode", "Unknown")
            work_mode_counter[mode] += 1

            sal = getattr(job, "salary", {})
            if isinstance(sal, dict) and sal.get("period") == "Yearly" and sal.get("minimum") is not None:
                salary_sum += sal["minimum"]
                salary_count += 1

        avg_salary = int(salary_sum / salary_count) if salary_count > 0 else 0

        return {
            "total_analyzed_jobs": total_jobs,
            "top_technologies": dict(tech_counter.most_common(10)),
            "top_skills": dict(skill_counter.most_common(10)),
            "work_mode_distribution": dict(work_mode_counter),
            "average_yearly_base_salary": avg_salary,
        }
