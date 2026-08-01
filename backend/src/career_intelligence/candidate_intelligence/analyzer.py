"""
CandidateAnalyzer — Derives CandidateContext from CandidateProfile

Analyzes raw resume facts in CandidateProfile to infer:
  - Inferred seniority level (intern, junior, mid, senior, staff, etc.)
  - Primary domain expertise (backend, frontend, ML, devops, etc.)
  - Capability vector (unified list of skills and technologies with confidence)
  - Total experience years
  - Education level

CandidateAnalyzer is strictly candidate-focused — it knows nothing about any job.

Invariant: Produces an immutable CandidateContext.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Set

from src.career_intelligence.candidate_intelligence.models import CandidateContext
from src.career_intelligence.job_intelligence.models import (
    Classification,
    Seniority,
)

logger = logging.getLogger("CandidateAnalyzer")

ANALYZER_VERSION = "1.0.0"


class CandidateAnalyzer:
    """Derives CandidateContext from a candidate profile object.

    Handles both career_intelligence.models.CandidateProfile (structured resume)
    and discovery.jie.candidate_profile.CandidateProfile (config/YAML).
    """

    # Domain signal maps
    _DOMAIN_SIGNALS: dict[str, list[str]] = {
        "backend": ["backend", "python", "java", "node", "fastapi", "django", "postgres", "redis", "rest", "api", "microservices", "go", "golang"],
        "frontend": ["frontend", "react", "vue", "angular", "javascript", "typescript", "html", "css", "next.js", "tailwind"],
        "fullstack": ["fullstack", "full stack", "full-stack"],
        "data_science": ["data science", "machine learning", "ml", "nlp", "pandas", "numpy", "pytorch", "tensorflow", "scikit-learn"],
        "devops": ["devops", "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "terraform", "linux"],
        "mobile": ["react native", "flutter", "ios", "android", "swift", "kotlin"],
        "product": ["product management", "product owner", "user research", "agile", "scrum", "jira"],
    }

    def analyze(self, profile: Any) -> CandidateContext:
        """Derive an immutable CandidateContext from a CandidateProfile.

        Args:
            profile: CandidateProfile instance (structured resume or config).

        Returns:
            An immutable CandidateContext.
        """
        years_exp = self._extract_experience_years(profile)
        skills, tech_list = self._extract_capabilities(profile)

        inferred_level = self._infer_seniority(profile, years_exp)
        domains = self._infer_domains(skills, tech_list, profile)
        capability_vector = self._build_capability_vector(skills, tech_list)
        edu_level = self._extract_education_level(profile)
        location = self._extract_location(profile)

        return CandidateContext(
            schema_version="2.0.0",
            inferred_level=inferred_level,
            primary_domains=domains,
            capability_vector=capability_vector,
            years_experience=years_exp,
            education_level=edu_level,
            current_location=location,
            analyzer_version=ANALYZER_VERSION,
            metadata={
                "extracted_skills_count": len(skills),
                "extracted_tech_count": len(tech_list),
            },
        )

    # ── Internal analysis methods ──

    def _extract_experience_years(self, profile: Any) -> float:
        """Calculate total experience years from profile attributes."""
        # 1. Attribute years_experience (from YAML/config or calculated field)
        if hasattr(profile, "years_experience") and profile.years_experience is not None:
            return float(profile.years_experience)

        # 2. Derive from experience items if present
        if hasattr(profile, "experience") and isinstance(profile.experience, list) and profile.experience:
            total_years = 0.0
            for exp in profile.experience:
                # If experience item has explicit start/end dates
                start = getattr(exp, "start_date", None)
                end = getattr(exp, "end_date", None)
                # Count ~1 year per entry as fallback if dates aren't parseable
                total_years += 1.0
            return max(0.5, total_years)

        return 0.0

    def _extract_capabilities(self, profile: Any) -> tuple[Set[str], Set[str]]:
        """Extract skills and technologies from profile."""
        skills: Set[str] = set()
        techs: Set[str] = set()

        # 1. Check if profile has CandidateSkills object
        if hasattr(profile, "skills"):
            s_obj = profile.skills
            if isinstance(s_obj, list):
                for s in s_obj:
                    skills.add(str(s))
            elif hasattr(s_obj, "programming_languages"):
                for cat in ["programming_languages", "frameworks", "libraries", "databases", "cloud", "ai_ml", "developer_tools", "other"]:
                    val = getattr(s_obj, cat, [])
                    if isinstance(val, list):
                        for item in val:
                            techs.add(str(item))

        # 2. Extract from experience entries
        if hasattr(profile, "experience") and isinstance(profile.experience, list):
            for exp in profile.experience:
                if hasattr(exp, "technologies") and isinstance(exp.technologies, list):
                    for t in exp.technologies:
                        techs.add(str(t))

        # 3. Extract from projects
        if hasattr(profile, "projects") and isinstance(profile.projects, list):
            for proj in profile.projects:
                if hasattr(proj, "technologies") and isinstance(proj.technologies, list):
                    for t in proj.technologies:
                        techs.add(str(t))

        return skills, techs

    def _infer_seniority(self, profile: Any, years_exp: float) -> Classification:
        """Infer candidate seniority level from role titles and experience years."""
        # Inspect role titles in experience history if available
        titles: List[str] = []
        if hasattr(profile, "experience") and isinstance(profile.experience, list):
            for exp in profile.experience:
                role = getattr(exp, "role", "")
                if role:
                    titles.append(str(role).lower())

        combined_titles = " ".join(titles)

        if any(w in combined_titles for w in ["principal", "staff"]):
            return Classification(value=Seniority.STAFF.value, confidence=0.9)
        if any(w in combined_titles for w in ["senior", "lead", "sr"]):
            return Classification(value=Seniority.SENIOR.value, confidence=0.9)
        if any(w in combined_titles for w in ["intern", "trainee"]):
            return Classification(value=Seniority.INTERN.value, confidence=0.9)

        # Fallback to experience years thresholds
        if years_exp >= 8.0:
            return Classification(value=Seniority.STAFF.value, confidence=0.7)
        if years_exp >= 4.0:
            return Classification(value=Seniority.SENIOR.value, confidence=0.8)
        if years_exp >= 2.0:
            return Classification(value=Seniority.MID.value, confidence=0.85)
        if years_exp > 0.0:
            return Classification(value=Seniority.JUNIOR.value, confidence=0.85)

        return Classification(value=Seniority.UNKNOWN.value, confidence=0.0)

    def _infer_domains(
        self,
        skills: Set[str],
        techs: Set[str],
        profile: Any,
    ) -> List[Classification]:
        """Infer candidate's primary domain expertise from capabilities and target roles."""
        combined_text = " ".join(list(skills) + list(techs)).lower()
        if hasattr(profile, "target_roles") and profile.target_roles:
            combined_text += " " + " ".join(profile.target_roles).lower()

        domains: List[Classification] = []
        for domain, signals in self._DOMAIN_SIGNALS.items():
            matches = sum(1 for sig in signals if sig in combined_text)
            if matches > 0:
                confidence = min(1.0, 0.4 + 0.15 * matches)
                domains.append(Classification(value=domain, confidence=round(confidence, 2)))

        domains.sort(key=lambda c: c.confidence, reverse=True)
        return domains

    def _build_capability_vector(
        self,
        skills: Set[str],
        techs: Set[str],
    ) -> List[Classification]:
        """Build normalized capability vector from extracted skills and technologies."""
        capabilities: List[Classification] = []
        seen: Set[str] = set()

        for item in list(techs) + list(skills):
            key = item.strip().lower()
            if key and key not in seen:
                seen.add(key)
                capabilities.append(Classification(value=item.strip(), confidence=1.0))

        return capabilities

    def _extract_education_level(self, profile: Any) -> str:
        """Extract highest degree achieved from education history or profile."""
        if hasattr(profile, "degree") and profile.degree:
            return str(profile.degree)
        if hasattr(profile, "education") and isinstance(profile.education, list) and profile.education:
            degrees = [str(getattr(e, "degree", "")) for e in profile.education if getattr(e, "degree", None)]
            if degrees:
                return degrees[0]
        return "None"

    def _extract_location(self, profile: Any) -> str:
        """Extract current location string from profile."""
        if hasattr(profile, "personal_info") and hasattr(profile.personal_info, "location"):
            loc = profile.personal_info.location
            if loc:
                return str(loc)
        if hasattr(profile, "location"):
            loc = profile.location
            if isinstance(loc, str):
                return loc
            if isinstance(loc, dict):
                parts = [loc.get(k) for k in ["city", "state", "country"] if loc.get(k)]
                return ", ".join(parts)
        return ""
