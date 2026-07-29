from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import re
import yaml
import os

_YEAR_RE = re.compile(r"(19|20)\d{2}")


class CandidateProfile(BaseModel):
    target_roles: List[str] = Field(default_factory=list)
    years_experience: int = 0
    graduation_year: Optional[int] = None
    degree: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_allowed: bool = True
    employment_types: List[str] = Field(default_factory=list)
    minimum_salary: Optional[float] = 0.0
    willing_to_relocate: bool = True
    citizenship: Optional[str] = None
    visa_status: Optional[str] = None
    clearance: Optional[str] = None
    preferred_domains: List[str] = Field(default_factory=list)
    preferred_company_size: List[str] = Field(default_factory=list)
    experience_text: str = ""

    @classmethod
    def from_yaml(cls, path: str = None) -> "CandidateProfile":
        if not path:
            path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "config", "candidate_profile.yaml")
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            # Fallback values
            return cls()

    @classmethod
    def from_profile_data(cls, profile_data: Dict[str, Any]) -> "CandidateProfile":
        """
        Builds a CandidateProfile from a candidate's real `user_career_profiles.profile_data`
        JSON (see ProfileDataPayload in api/routers/candidate.py), instead of the static
        single-tenant YAML config. Missing/unfilled fields fall back to permissive defaults
        rather than rejecting jobs on data we simply don't have yet.
        """
        profile_data = profile_data or {}
        prefs = profile_data.get("career_preferences") or {}
        personal = profile_data.get("personal_info") or {}
        experience = profile_data.get("experience") or []
        education = profile_data.get("education") or []
        projects = profile_data.get("projects") or []
        skills_by_category = profile_data.get("skills") or {}

        experience_text_parts: List[str] = []
        for entry in experience:
            desc = (entry or {}).get("description")
            if desc:
                experience_text_parts.append(str(desc))
        for entry in projects:
            desc = (entry or {}).get("description")
            if desc:
                experience_text_parts.append(str(desc))
        experience_text = " ".join(experience_text_parts)

        target_roles: List[str] = []
        desired_role = (prefs.get("desired_role") or "").strip()
        if desired_role:
            target_roles = [r.strip() for r in desired_role.split(",") if r.strip()]

        years_experience = cls._estimate_years_experience(experience)

        skills: List[str] = []
        for group in skills_by_category.values():
            if isinstance(group, list):
                skills.extend(s for s in group if isinstance(s, str) and s.strip())

        preferred_locations: List[str] = []
        locations_raw = (prefs.get("locations") or "").strip()
        if locations_raw:
            preferred_locations = [l.strip() for l in locations_raw.split(",") if l.strip()]
        elif personal.get("location"):
            preferred_locations = [personal["location"]]

        work_type = (prefs.get("work_type") or "").strip().lower()
        remote_allowed = True if not work_type else ("remote" in work_type or "hybrid" in work_type)

        minimum_salary = 0.0
        salary_raw = str(prefs.get("min_salary") or "").strip()
        if salary_raw:
            digits = re.sub(r"[^\d.]", "", salary_raw)
            try:
                minimum_salary = float(digits) if digits else 0.0
            except ValueError:
                minimum_salary = 0.0

        degree = None
        for entry in education:
            d = str((entry or {}).get("degree") or "")
            if re.search(r"\bph\.?d\b|doctorate", d, re.IGNORECASE):
                degree = "PhD"
                break
        if degree is None and education:
            degree = (education[0] or {}).get("degree") or None

        return cls(
            target_roles=target_roles,
            years_experience=years_experience,
            graduation_year=None,
            degree=degree,
            skills=skills,
            preferred_locations=preferred_locations,
            remote_allowed=remote_allowed,
            employment_types=["Full-time"],
            minimum_salary=minimum_salary,
            willing_to_relocate=bool(prefs.get("open_to_relocation", True)),
            citizenship=None,
            visa_status=None,
            clearance=None,
            preferred_domains=[],
            preferred_company_size=[],
            experience_text=experience_text,
        )

    @staticmethod
    def _estimate_years_experience(experience: List[Dict[str, Any]]) -> int:
        """
        Crude, deterministic (no-LLM) estimate: earliest start year to latest end year
        (or current year if any entry is ongoing) across all experience entries.
        """
        import datetime

        years: List[int] = []
        has_ongoing = False
        for entry in experience:
            entry = entry or {}
            start = str(entry.get("start_date") or "")
            end = str(entry.get("end_date") or "")
            m = _YEAR_RE.search(start)
            if m:
                years.append(int(m.group(0)))
            if re.search(r"present|current|now", end, re.IGNORECASE) or not end.strip():
                has_ongoing = True
            else:
                m2 = _YEAR_RE.search(end)
                if m2:
                    years.append(int(m2.group(0)))

        if not years:
            return 0

        latest = datetime.datetime.now().year if has_ongoing else max(years)
        return max(0, latest - min(years))
