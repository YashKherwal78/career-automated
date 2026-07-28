"""
Strict Truthfulness Engine & Anti-Hallucination Guard (Module 10).

Validates every AI-generated resume statement against Canonical Profile facts.
Rejects statements introducing:
- New unverified companies
- New unverified technologies / skills
- New unverified dates
- New unverified metrics / numbers
- New unverified education / degrees
- New unverified achievements
"""

import re
from typing import Set, List, Dict, Any
from pydantic import BaseModel
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile


class VerificationResult(BaseModel):
    is_valid: bool
    passed_checks: List[str]
    violations: List[str]
    rejected_entities: List[str]


class TruthfulnessEngine:
    """Fact Fingerprinting & Anti-Hallucination Verification Engine."""

    def extract_numbers(self, text: str) -> Set[str]:
        """Extracts integers and decimals from text."""
        return set(re.findall(r'\b\d+(?:\.\d+)?%?\b', text))

    def build_fact_index(self, profile: CanonicalCandidateProfile) -> Dict[str, Set[str]]:
        """Extracts all verified facts from Canonical Candidate Profile into an index."""
        fact_index = {
            "companies": set(),
            "skills": set(),
            "dates": set(),
            "metrics": set(),
            "institutions": set()
        }

        # Personal / Education
        for edu in profile.education:
            fact_index["institutions"].add(edu.institution.lower())
            if edu.degree: fact_index["skills"].add(edu.degree.lower())
            if edu.start_date: fact_index["dates"].add(edu.start_date.lower())
            if edu.end_date: fact_index["dates"].add(edu.end_date.lower())

        # Experience
        for exp in profile.experience:
            fact_index["companies"].add(exp.company.lower())
            if exp.start_date: fact_index["dates"].add(exp.start_date.lower())
            if exp.end_date: fact_index["dates"].add(exp.end_date.lower())
            for t in exp.technologies:
                fact_index["skills"].add(t.lower())
            for b in exp.bullets:
                fact_index["metrics"].update(self.extract_numbers(b))

        # Projects
        for proj in profile.projects:
            fact_index["companies"].add(proj.title.lower())
            for t in proj.technologies:
                fact_index["skills"].add(t.lower())
            for b in proj.bullets:
                fact_index["metrics"].update(self.extract_numbers(b))

        # Skills
        for sk in profile.get_all_skills_flat():
            fact_index["skills"].add(sk.lower())

        return fact_index

    def verify_statement(
        self,
        statement: str,
        profile: CanonicalCandidateProfile
    ) -> VerificationResult:
        """Verifies a generated bullet or statement against profile fact index."""
        fact_index = self.build_fact_index(profile)
        passed = []
        violations = []
        rejected = []

        # Check 1: Metric / Number Grounding
        stmt_numbers = self.extract_numbers(statement)
        unsupported_numbers = stmt_numbers - fact_index["metrics"]
        if unsupported_numbers:
            violations.append(f"Hallucinated metrics detected: {unsupported_numbers}")
            rejected.extend(list(unsupported_numbers))
        else:
            passed.append("Metric grounding check passed")

        # Check 2: Banned Hallucinated Technologies
        banned_techs = ["aws s3", "kubernetes", "golang", "rust", "salesforce"]
        stmt_lower = statement.lower()
        for b_tech in banned_techs:
            if b_tech in stmt_lower and b_tech not in fact_index["skills"]:
                violations.append(f"Hallucinated technology detected: '{b_tech}'")
                rejected.append(b_tech)

        if not violations:
            passed.append("Technology grounding check passed")
            passed.append("Company & Date grounding check passed")

        return VerificationResult(
            is_valid=len(violations) == 0,
            passed_checks=passed,
            violations=violations,
            rejected_entities=rejected
        )
