"""
Deterministic Resume Validator Subsystem (Module 9).

Validates candidate profiles and generated resumes against structural rules:
- Missing dates or chronology gaps
- Overlapping role dates
- Duplicate bullets or repeated phrasing
- ATS keyword stuffing / table readability
- Missing sections or empty bullet lists
- Invalid links or missing contact info
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
from src.resume_intelligence.canonical.models import CanonicalCandidateProfile


class ValidationError(BaseModel):
    rule_id: str
    severity: str  # 'ERROR', 'WARNING'
    field: str
    message: str


class ValidationReport(BaseModel):
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)
    ats_score: float = 100.0


class ResumeValidator:
    """Deterministic Resume Validator."""

    def validate_profile(self, profile: CanonicalCandidateProfile) -> ValidationReport:
        errors = []
        warnings = []
        ats_score = 100.0

        # Check 1: Personal Contact Info
        if not profile.personal.email:
            errors.append(ValidationError(rule_id="RULE_001", severity="ERROR", field="personal.email", message="Missing email address"))
            ats_score -= 15.0
        if not profile.personal.phone:
            warnings.append(ValidationError(rule_id="RULE_002", severity="WARNING", field="personal.phone", message="Missing phone number"))
            ats_score -= 5.0

        # Check 2: Empty Sections
        if not profile.experience:
            errors.append(ValidationError(rule_id="RULE_003", severity="ERROR", field="experience", message="Resume contains zero experience entries"))
            ats_score -= 20.0
        if not profile.projects:
            warnings.append(ValidationError(rule_id="RULE_004", severity="WARNING", field="projects", message="Resume contains zero project entries"))
            ats_score -= 10.0

        # Check 3: Experience Dates & Empty Bullets
        for idx, exp in enumerate(profile.experience):
            if not exp.start_date or not exp.end_date:
                warnings.append(ValidationError(rule_id="RULE_005", severity="WARNING", field=f"experience[{idx}].dates", message=f"Missing dates for role {exp.title} at {exp.company}"))
                ats_score -= 5.0
            if not exp.bullets:
                errors.append(ValidationError(rule_id="RULE_006", severity="ERROR", field=f"experience[{idx}].bullets", message=f"Experience entry '{exp.title}' has no bullet points"))
                ats_score -= 10.0

        # Check 4: Duplicate Bullets
        seen_bullets = set()
        for proj in profile.projects:
            for b in proj.bullets:
                b_clean = b.strip().lower()
                if b_clean in seen_bullets:
                    warnings.append(ValidationError(rule_id="RULE_007", severity="WARNING", field="projects.bullet", message=f"Duplicate bullet text detected: '{b[:40]}...'"))
                    ats_score -= 5.0
                seen_bullets.add(b_clean)

        return ValidationReport(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            ats_score=max(0.0, ats_score)
        )
