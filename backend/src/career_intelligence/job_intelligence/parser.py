"""
JobParser — Stage 1: Raw Fact Extraction

Extracts explicitly present attributes from job description text into a
ParsedJob. No semantic inference or classification happens here.

Delegates to the existing JIE sub-extractors for consistency. The parser
is candidate-agnostic — it knows nothing about any candidate.

Invariant: ParsedJob is immutable once produced.
"""

from __future__ import annotations

import datetime
import hashlib
import logging
from typing import Any, Dict, List, Optional

from src.career_intelligence.job_intelligence.models import (
    LocationInfo,
    ParsedJob,
    ParsedRequirement,
    SalaryInfo,
)
from src.discovery.jie.extractors.basic import extract_basic_info
from src.discovery.jie.extractors.benefits import extract_benefits
from src.discovery.jie.extractors.dates import extract_dates
from src.discovery.jie.extractors.education import EducationExtractor
from src.discovery.jie.extractors.employment_type import extract_employment_type
from src.discovery.jie.extractors.experience import ExperienceExtractor
from src.discovery.jie.extractors.location import extract_location
from src.discovery.jie.extractors.preprocessing import preprocess_jd
from src.discovery.jie.extractors.requirements import extract_requirements, generate_legacy_requirements
from src.discovery.jie.extractors.responsibilities import extract_responsibilities
from src.discovery.jie.extractors.salary import extract_salary
from src.discovery.jie.extractors.skills import SkillExtractor
from src.discovery.jie.extractors.technologies import TechnologyExtractor

logger = logging.getLogger("JobParser")

PARSER_VERSION = "2.0.0"


class JobParser:
    """Extracts raw facts from job description text into a ParsedJob.

    Reuses existing JIE sub-extractors under the hood but produces
    the new Phase 2 ParsedJob schema instead of the legacy StructuredJob.

    Usage:
        parser = JobParser()
        parsed = parser.parse(title="Backend Engineer", jd_text="...", metadata={})
    """

    def __init__(self) -> None:
        self._experience_extractor = ExperienceExtractor()
        self._education_extractor = EducationExtractor()
        self._technology_extractor = TechnologyExtractor()
        self._skill_extractor = SkillExtractor()

    def parse(
        self,
        title: str,
        jd_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ParsedJob:
        """Parse a job description into a ParsedJob.

        Args:
            title:    The raw job title.
            jd_text:  The full job description text.
            metadata: Optional dict with hints (e.g. domain, job_url).

        Returns:
            An immutable ParsedJob containing only extracted facts.
        """
        if metadata is None:
            metadata = {}

        jd_hash = hashlib.md5(jd_text.encode("utf-8")).hexdigest()
        parsed_at = (
            datetime.datetime.now(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        clean_text = preprocess_jd(jd_text)

        # ── Delegate to JIE sub-extractors ──
        basic = extract_basic_info(title, clean_text, metadata)
        loc = extract_location(clean_text, title, metadata)
        emp_type = extract_employment_type(title, clean_text)
        exp = self._experience_extractor.extract(clean_text)
        edu = self._education_extractor.extract(clean_text)
        techs = self._technology_extractor.extract(clean_text)
        skills = self._skill_extractor.extract(clean_text)
        sal = extract_salary(clean_text)
        resp = extract_responsibilities(clean_text)
        raw_reqs = extract_requirements(clean_text)
        benefits = extract_benefits(clean_text)
        dates = extract_dates(clean_text)

        # ── Build structured sub-models ──
        location = self._build_location(loc)
        salary = self._build_salary(sal)
        requirements = self._build_requirements(raw_reqs, techs, skills)

        edu_list = edu.degrees + edu.fields

        return ParsedJob(
            schema_version=PARSER_VERSION,
            jd_hash=jd_hash,
            parsed_at=parsed_at,
            title=basic["title"],
            company=basic["company"],
            job_url=basic.get("job_url", metadata.get("job_url", "")),
            job_id=basic.get("job_id", metadata.get("job_id", "")),
            location=location,
            work_mode=loc.get("work_mode", "Unknown"),
            employment_type=emp_type,
            experience_min=exp.experience_min,
            experience_max=exp.experience_max,
            fresher_friendly=exp.fresher_friendly,
            salary=salary,
            education=edu_list,
            technologies=techs if isinstance(techs, list) else [],
            skills=skills if isinstance(skills, list) else [],
            requirements=requirements,
            responsibilities=resp,
            benefits=benefits,
            visa_sponsorship=self._detect_visa(clean_text),
            posted_date=dates.get("posted_date"),
            application_deadline=dates.get("application_deadline"),
            domain_hint=metadata.get("domain", "Unknown"),
            parser_metadata={
                "ats_provider": basic.get("ats_provider", "unknown"),
                "raw_requirements": raw_reqs,
                "parser_version": PARSER_VERSION,
            },
        )

    # ── Private helpers ──

    @staticmethod
    def _build_location(loc: Dict[str, Any]) -> LocationInfo:
        """Convert legacy location dict to LocationInfo model."""
        raw_loc = loc.get("location", {})
        if isinstance(raw_loc, dict):
            return LocationInfo(
                country=raw_loc.get("country", ""),
                state=raw_loc.get("state", ""),
                city=raw_loc.get("city", ""),
                raw=str(raw_loc),
            )
        return LocationInfo(raw=str(raw_loc))

    @staticmethod
    def _build_salary(sal: Dict[str, Any]) -> SalaryInfo:
        """Convert legacy salary dict to SalaryInfo model."""
        if isinstance(sal, dict):
            return SalaryInfo(
                currency=sal.get("currency", ""),
                minimum=sal.get("minimum"),
                maximum=sal.get("maximum"),
                period=sal.get("period", ""),
            )
        return SalaryInfo()

    @staticmethod
    def _build_requirements(
        raw_reqs: Any,
        techs: Any,
        skills: Any,
    ) -> List[ParsedRequirement]:
        """Build ParsedRequirement list from raw extraction results.

        Merges explicit requirements with technologies and skills,
        deduplicating by name.

        Note: raw_reqs from JIE's extract_requirements() is List[str],
        not List[Dict]. Each entry is a raw text line from the JD.
        """
        seen: set = set()
        requirements: List[ParsedRequirement] = []

        # Explicit requirements from the requirement extractor
        # JIE returns List[str] — each item is a requirement text line
        req_list = raw_reqs if isinstance(raw_reqs, list) else []
        for req in req_list:
            if isinstance(req, str):
                name = req.strip()
                if not name or name.lower() in seen:
                    continue
                seen.add(name.lower())
                requirements.append(
                    ParsedRequirement(
                        category="requirement",
                        name=name,
                        importance="REQUIRED",
                        confidence=0.8,
                        evidence=name,
                    )
                )
            elif isinstance(req, dict):
                name = req.get("name") or req.get("text", "")
                if not name or name.lower() in seen:
                    continue
                seen.add(name.lower())
                requirements.append(
                    ParsedRequirement(
                        category=req.get("type", "skill"),
                        name=name,
                        importance=req.get("importance", "REQUIRED"),
                        confidence=float(req.get("confidence", 1.0)),
                        evidence=req.get("evidence", ""),
                    )
                )

        # Technologies
        tech_list = techs if isinstance(techs, list) else []
        for tech in tech_list:
            if tech.lower() not in seen:
                seen.add(tech.lower())
                requirements.append(
                    ParsedRequirement(
                        category="technology",
                        name=tech,
                        importance="REQUIRED",
                        confidence=0.9,
                    )
                )

        # Skills
        skill_list = skills if isinstance(skills, list) else []
        for skill in skill_list:
            if skill.lower() not in seen:
                seen.add(skill.lower())
                requirements.append(
                    ParsedRequirement(
                        category="skill",
                        name=skill,
                        importance="PREFERRED",
                        confidence=0.85,
                    )
                )

        return requirements

    @staticmethod
    def _detect_visa(text: str) -> str:
        """Detect visa sponsorship availability from job text."""
        text_lower = text.lower()
        no_sponsor = [
            "no sponsorship available",
            "no visa sponsorship",
            "we do not sponsor",
            "cannot provide sponsorship",
            "do not provide sponsorship",
            "without sponsorship",
        ]
        yes_sponsor = [
            "visa sponsorship available",
            "we sponsor",
            "sponsorship provided",
            "visa sponsorship is available",
        ]
        if any(p in text_lower for p in no_sponsor):
            return "No"
        if any(p in text_lower for p in yes_sponsor):
            return "Yes"
        return "Unknown"
