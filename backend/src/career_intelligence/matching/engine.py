from typing import Dict, Any, List
from src.career_intelligence.interfaces import ScorerInterface
from src.career_intelligence.models import ComparisonResult, MatchScore, ScoreBreakdown
from src.career_intelligence.matching.config import MatchingConfig

class MatchScoreEngine(ScorerInterface):
    def __init__(self, config: MatchingConfig = None):
        self.config = config or MatchingConfig()

    def calculate_score(self, comparison: ComparisonResult) -> MatchScore:
        """Calculates MatchScore and confidence metrics directly from a ComparisonResult."""
        
        # 1. Calculate category percentages
        total_skills = len(comparison.matched_skills) + len(comparison.missing_skills)
        skills_score = int((len(comparison.matched_skills) / total_skills * 100)) if total_skills > 0 else 100

        total_techs = len(comparison.matched_technologies) + len(comparison.missing_technologies)
        tech_score = int((len(comparison.matched_technologies) / total_techs * 100)) if total_techs > 0 else 100

        exp_score = 100 if comparison.experience_fit else max(0, int(100 - (comparison.experience_gap * 10)))
        edu_score = 100 if comparison.education_fit else 0
        loc_score = 100 if comparison.location_fit else 50
        work_mode_score = 100 if comparison.work_mode_fit else 50
        emp_score = 100 if comparison.employment_type_fit else 50
        
        total_certs = len(comparison.matched_certifications) + len(comparison.missing_certifications)
        cert_score = int((len(comparison.matched_certifications) / total_certs * 100)) if total_certs > 0 else 100

        breakdown = ScoreBreakdown(
            skills=skills_score,
            technologies=tech_score,
            experience=exp_score,
            projects=100 if comparison.matched_projects else 50,
            education=edu_score,
            location=int((loc_score + work_mode_score) / 2),
            employment=emp_score,
            certifications=cert_score
        )

        # 2. Weighted overall score calculation
        overall = 0.0
        total_weight = 0.0
        
        categories = {
            "skills": breakdown.skills,
            "technologies": breakdown.technologies,
            "experience": breakdown.experience,
            "projects": breakdown.projects,
            "education": breakdown.education,
            "location": breakdown.location,
            "employment": breakdown.employment,
            "certifications": breakdown.certifications
        }

        for cat, val in categories.items():
            weight = self.config.get_weight(cat)
            overall += val * weight
            total_weight += weight

        overall_score = int(overall / total_weight) if total_weight > 0 else 100

        # 3. Confidence Score calculation
        # Confidence reflects how complete the profile and parsed data is (ranges 0-100)
        confidence = 100
        if not comparison.matched_skills and not comparison.missing_skills:
            confidence -= 15
        if not comparison.matched_technologies and not comparison.missing_technologies:
            confidence -= 15
        if comparison.experience_candidate == 0.0:
            confidence -= 10
        confidence = max(50, confidence)

        # Match level & Grade classification
        if overall_score >= 90:
            grade = "A"
            match_level = "Excellent"
        elif overall_score >= 80:
            grade = "B"
            match_level = "Good"
        elif overall_score >= 65:
            grade = "C"
            match_level = "Fair"
        else:
            grade = "D"
            match_level = "Poor"

        # Build list of critical missing elements
        critical_missing = comparison.critical_missing_skills + comparison.missing_technologies[:2]

        return MatchScore(
            overall_score=overall_score,
            confidence=confidence,
            grade=grade,
            match_level=match_level,
            breakdown=breakdown,
            strengths=comparison.strengths,
            weaknesses=comparison.weaknesses,
            critical_missing=critical_missing,
            summary=f"Candidate is a {match_level} match ({overall_score}%) with a parsing confidence of {confidence}%."
        )
