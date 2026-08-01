"""
JobEnricher — Stage 2: Semantic Enrichment

Takes a ParsedJob and produces a StructuredJob by inferring:
  - Seniority level
  - Primary domains
  - Capability vector
  - Job family classification

The enricher is entirely candidate-agnostic — it knows nothing about
any candidate. It only reasons about the job itself.

Invariant: StructuredJob is immutable once produced.
"""

from __future__ import annotations

import logging
import re
from typing import List

from src.career_intelligence.job_intelligence.models import (
    Classification,
    ParsedJob,
    Seniority,
    StructuredJob,
)

logger = logging.getLogger("JobEnricher")

ENRICHER_VERSION = "1.0.0"


class JobEnricher:
    """Enriches a ParsedJob with semantic classifications.

    Usage:
        enricher = JobEnricher()
        structured = enricher.enrich(parsed_job)
    """

    # ── Seniority keyword mapping ──
    # Order matters: more senior titles are checked first to avoid
    # "senior" matching before "staff senior".
    _SENIORITY_PATTERNS: list[tuple[Seniority, list[str]]] = [
        (Seniority.C_LEVEL, [r"\bceo\b", r"\bcto\b", r"\bcfo\b", r"\bcoo\b", r"\bc-level\b"]),
        (Seniority.VP, [r"\bvice president\b", r"\bvp\b"]),
        (Seniority.DIRECTOR, [r"\bdirector\b"]),
        (Seniority.PRINCIPAL, [r"\bprincipal\b"]),
        (Seniority.STAFF, [r"\bstaff\b"]),
        (Seniority.SENIOR, [r"\bsenior\b", r"\bsr\.?\b", r"\bsr\b"]),
        (Seniority.JUNIOR, [r"\bjunior\b", r"\bjr\.?\b", r"\bjr\b", r"\bentry[- ]level\b"]),
        (Seniority.INTERN, [r"\bintern\b", r"\binternship\b"]),
    ]

    # ── Domain keyword mapping ──
    _DOMAIN_SIGNALS: dict[str, list[str]] = {
        "backend": ["backend", "server-side", "api development", "rest api", "microservices"],
        "frontend": ["frontend", "front-end", "ui development", "react", "angular", "vue"],
        "fullstack": ["fullstack", "full-stack", "full stack"],
        "data_engineering": ["data engineering", "data pipeline", "etl", "data warehouse", "airflow", "spark"],
        "data_science": ["data science", "data scientist", "statistical modeling", "analytics"],
        "machine_learning": ["machine learning", "deep learning", "ml engineer", "ai engineer", "nlp", "computer vision"],
        "devops": ["devops", "sre", "site reliability", "infrastructure", "ci/cd", "kubernetes", "docker"],
        "mobile": ["mobile", "ios", "android", "react native", "flutter", "swift", "kotlin"],
        "security": ["security", "cybersecurity", "infosec", "penetration testing", "soc"],
        "cloud": ["cloud", "aws", "azure", "gcp", "cloud architect"],
        "product": ["product manager", "product management", "product owner"],
        "design": ["ux", "ui/ux", "product design", "interaction design"],
        "qa": ["quality assurance", "qa engineer", "test engineer", "sdet"],
        "embedded": ["embedded", "firmware", "iot", "rtos"],
        "blockchain": ["blockchain", "web3", "smart contract", "solidity"],
        "game_dev": ["game developer", "game engine", "unity", "unreal"],
    }

    # ── Job family mapping ──
    _JOB_FAMILY_SIGNALS: dict[str, list[str]] = {
        "software_engineering": [
            "software engineer", "developer", "programmer", "swe", "sde",
            "backend engineer", "frontend engineer", "fullstack", "full stack",
            "full-stack", "backend", "frontend", "software",
        ],
        "data_science": [
            "data scientist", "research scientist", "ml engineer",
            "machine learning", "ai engineer",
        ],
        "product_management": [
            "product manager", "apm", "associate product",
            "technical product manager", "product owner",
        ],
        "devops_sre": [
            "devops", "sre", "platform engineer", "infrastructure engineer",
            "cloud engineer", "site reliability",
        ],
        "design": [
            "product designer", "ux designer", "ui designer",
            "interaction designer", "visual designer",
        ],
        "qa_testing": [
            "qa engineer", "test engineer", "sdet", "quality assurance",
        ],
        "data_engineering": [
            "data engineer", "analytics engineer", "etl developer",
            "data architect",
        ],
        "management": [
            "engineering manager", "tech lead", "director of engineering",
            "vp engineering", "head of engineering",
        ],
        "security": [
            "security engineer", "appsec", "infosec",
            "security analyst", "penetration tester",
        ],
    }

    def enrich(self, parsed: ParsedJob) -> StructuredJob:
        """Produce a semantically enriched StructuredJob from a ParsedJob.

        Args:
            parsed: An immutable ParsedJob from JobParser.

        Returns:
            An immutable StructuredJob with inferred classifications.
        """
        title_lower = parsed.title.lower()
        combined_text = f"{parsed.title} {' '.join(parsed.responsibilities)} {' '.join(parsed.skills)}"
        combined_lower = combined_text.lower()

        seniority = self._infer_seniority(title_lower, parsed.experience_min)
        domains = self._infer_domains(combined_lower, parsed.technologies)
        capabilities = self._infer_capabilities(parsed)
        job_family = self._infer_job_family(title_lower, combined_lower)

        return StructuredJob(
            schema_version=parsed.schema_version,
            jd_hash=parsed.jd_hash,
            parsed_at=parsed.parsed_at,
            title=parsed.title,
            company=parsed.company,
            job_url=parsed.job_url,
            job_id=parsed.job_id,
            location=parsed.location,
            work_mode=parsed.work_mode,
            employment_type=parsed.employment_type,
            experience_min=parsed.experience_min,
            experience_max=parsed.experience_max,
            fresher_friendly=parsed.fresher_friendly,
            salary=parsed.salary,
            education=parsed.education,
            technologies=parsed.technologies,
            skills=parsed.skills,
            requirements=parsed.requirements,
            responsibilities=parsed.responsibilities,
            benefits=parsed.benefits,
            certifications_required=parsed.certifications_required,
            visa_sponsorship=parsed.visa_sponsorship,
            posted_date=parsed.posted_date,
            application_deadline=parsed.application_deadline,
            seniority=seniority,
            domains=domains,
            capabilities=capabilities,
            job_family=job_family,
            enricher_version=ENRICHER_VERSION,
            parser_metadata=parsed.parser_metadata,
        )

    # ── Private inference methods ──

    def _infer_seniority(
        self,
        title_lower: str,
        experience_min: int | None,
    ) -> Classification:
        """Infer seniority from title keywords and experience range."""
        for level, patterns in self._SENIORITY_PATTERNS:
            for pat in patterns:
                if re.search(pat, title_lower):
                    return Classification(value=level.value, confidence=0.9)

        # Fallback: infer from experience requirements
        if experience_min is not None:
            if experience_min >= 10:
                return Classification(value=Seniority.STAFF.value, confidence=0.5)
            if experience_min >= 5:
                return Classification(value=Seniority.SENIOR.value, confidence=0.5)
            if experience_min >= 2:
                return Classification(value=Seniority.MID.value, confidence=0.5)
            if experience_min == 0:
                return Classification(value=Seniority.JUNIOR.value, confidence=0.5)

        return Classification(value=Seniority.UNKNOWN.value, confidence=0.0)

    def _infer_domains(
        self,
        combined_lower: str,
        technologies: list[str],
    ) -> List[Classification]:
        """Infer relevant domains from text signals and technology stack."""
        domains: List[Classification] = []
        tech_lower = " ".join(t.lower() for t in technologies)
        search_text = f"{combined_lower} {tech_lower}"

        for domain, signals in self._DOMAIN_SIGNALS.items():
            match_count = sum(1 for sig in signals if sig in search_text)
            if match_count > 0:
                # Confidence scales with number of signals matched
                confidence = min(1.0, 0.5 + 0.15 * match_count)
                domains.append(Classification(value=domain, confidence=round(confidence, 2)))

        # Sort by confidence descending
        domains.sort(key=lambda c: c.confidence, reverse=True)
        return domains

    def _infer_capabilities(self, parsed: ParsedJob) -> List[Classification]:
        """Build capability vector from extracted skills and technologies.

        Each technology and skill becomes a capability with its extraction
        confidence preserved.
        """
        seen: set[str] = set()
        capabilities: List[Classification] = []

        for req in parsed.requirements:
            key = req.name.lower()
            if key not in seen:
                seen.add(key)
                capabilities.append(
                    Classification(value=req.name, confidence=req.confidence)
                )

        # Add technologies and skills not already covered
        for tech in parsed.technologies:
            key = tech.lower()
            if key not in seen:
                seen.add(key)
                capabilities.append(Classification(value=tech, confidence=0.9))

        for skill in parsed.skills:
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                capabilities.append(Classification(value=skill, confidence=0.85))

        return capabilities

    def _infer_job_family(
        self,
        title_lower: str,
        combined_lower: str,
    ) -> Classification:
        """Infer the job family from title and description signals."""
        best_family = "unknown"
        best_score = 0

        for family, signals in self._JOB_FAMILY_SIGNALS.items():
            score = 0
            for sig in signals:
                # Title matches weight more than body matches
                if sig in title_lower:
                    score += 3
                elif sig in combined_lower:
                    score += 1
            if score > best_score:
                best_score = score
                best_family = family

        confidence = min(1.0, best_score * 0.2) if best_score > 0 else 0.0
        return Classification(value=best_family, confidence=round(confidence, 2))
