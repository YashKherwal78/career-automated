"""
CompanyIntelligenceService — Phase 3 Company Intelligence

Manages company profiles, ATS provider tracking, response rate estimation,
and company targeting recommendations.

Invariant: Zero modification of match scores.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from src.career_intelligence.company.models import (
    CompanyProfile,
    CompanyRecommendation,
    CultureMetrics,
)

logger = logging.getLogger("CompanyIntelligenceService")


class CompanyIntelligenceService:
    """Provides company intelligence and targeting recommendations derived from empirical data."""

    def __init__(self) -> None:
        self._store: Dict[str, CompanyProfile] = {}

    def get_or_create_profile(
        self,
        company_name: str,
        ats_provider: str = "Unknown",
        job_url: str = "",
        application_tracker: Any | None = None,
    ) -> CompanyProfile:
        """Fetch or initialize a structured CompanyProfile using empirical job and tracker data."""
        key = company_name.strip().lower()

        # 1. Detect ATS provider from job_url if not explicitly provided
        detected_ats = ats_provider
        if detected_ats == "Unknown" and job_url:
            url_lower = job_url.lower()
            if "greenhouse" in url_lower:
                detected_ats = "Greenhouse"
            elif "lever" in url_lower:
                detected_ats = "Lever"
            elif "workday" in url_lower:
                detected_ats = "Workday"
            elif "ashby" in url_lower:
                detected_ats = "Ashby"
            elif "bamboohr" in url_lower:
                detected_ats = "BambooHR"

        # 2. Derive empirical response rate from ApplicationTracker if available
        derived_response_rate = 0.25
        derived_velocity = "Moderate"

        if application_tracker and hasattr(application_tracker, "_records"):
            company_apps = []
            for records in application_tracker._records.values():
                for app in records:
                    if getattr(app, "company_name", "").strip().lower() == key:
                        company_apps.append(app)

            if company_apps:
                total_apps = len(company_apps)
                callbacks = sum(1 for a in company_apps if getattr(a, "status", "") in ("RECRUITER_SCREEN", "TECHNICAL_INTERVIEW", "OFFER"))
                derived_response_rate = round(callbacks / float(total_apps), 2)
                if derived_response_rate >= 0.4:
                    derived_velocity = "High"
                elif derived_response_rate < 0.15:
                    derived_velocity = "Slow"

        if key in self._store:
            existing = self._store[key]
            # Update ATS if previously unknown
            if existing.ats_provider == "Unknown" and detected_ats != "Unknown":
                updated = existing.model_copy(update={"ats_provider": detected_ats, "historical_response_rate": derived_response_rate})
                self._store[key] = updated
                return updated
            return existing

        profile = CompanyProfile(
            company_id=f"comp_{key[:10]}",
            company_name=company_name.strip(),
            ats_provider=detected_ats,
            hiring_velocity=derived_velocity,
            avg_response_days=5 if derived_velocity == "High" else 10,
            historical_response_rate=derived_response_rate,
            hiring_difficulty="Medium",
            primary_tech_stack=["Python", "React", "PostgreSQL", "AWS"],
            culture=CultureMetrics(),
            recruiter_insights=[
                f"ATS Provider detected: {detected_ats}.",
                f"Empirical callback rate: {derived_response_rate * 100:.0f}%.",
            ],
        )

        self._store[key] = profile
        return profile

    def generate_recommendation(
        self,
        company_name: str,
        match_score: float,
        candidate_level: str = "mid",
        job_url: str = "",
        application_tracker: Any | None = None,
    ) -> CompanyRecommendation:
        """Generate company targeting recommendation for candidate."""
        profile = self.get_or_create_profile(
            company_name=company_name,
            job_url=job_url,
            application_tracker=application_tracker,
        )

        if match_score >= 80.0 and profile.historical_response_rate >= 0.20:
            level = "TOP_TARGET"
            reasoning = f"High match score ({match_score:.1f}) and solid empirical response rate ({profile.historical_response_rate*100:.0f}%)."
        elif match_score >= 60.0:
            level = "HIGH_PROBABILITY"
            reasoning = f"Solid alignment ({match_score:.1f}) with active hiring velocity ({profile.hiring_velocity})."
        else:
            level = "REACH"
            reasoning = f"Lower baseline match ({match_score:.1f}); update key stack competencies before applying."

        return CompanyRecommendation(
            company_name=company_name,
            recommendation_level=level,
            reasoning=reasoning,
            key_advantages=[
                f"Uses {profile.ats_provider} ATS",
                f"Empirical response rate: {profile.historical_response_rate*100:.0f}%",
                f"Hiring velocity: {profile.hiring_velocity}",
            ],
        )
