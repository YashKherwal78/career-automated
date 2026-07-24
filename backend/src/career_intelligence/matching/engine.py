from typing import Dict, Any, List
from src.career_intelligence.interfaces import ScorerInterface
from src.career_intelligence.models import ComparisonResult, MatchScore, ScoreBreakdown
from src.career_intelligence.matching.config import MatchingConfig

class MatchScoreEngine(ScorerInterface):
    def __init__(self, config: MatchingConfig = None):
        self.config = config or MatchingConfig()

    def calculate_score(self, comparison: ComparisonResult) -> MatchScore:
        """Calculates MatchScore and confidence metrics directly from hierarchical ComparisonResult scores."""
        breakdown = ScoreBreakdown(
            skills=int(comparison.skills.score * 100),
            technologies=int(comparison.technologies.score * 100),
            experience=int(comparison.experience.score * 100),
            projects=int(comparison.projects.score * 100),
            education=int(comparison.education.score * 100),
            location=int(comparison.location.score * 100),
            employment=int(comparison.employment.score * 100),
            certifications=int(comparison.certifications.score * 100)
        )

        # Weighted overall score calculation
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

        # Confidence Score calculation
        # Confidence reflects how complete the profile and parsed data is
        confidence = 100
        if not comparison.skills.matched and not comparison.skills.missing:
            confidence -= 15
        if not comparison.technologies.matched and not comparison.technologies.missing:
            confidence -= 15
            
        exp_meta = comparison.experience.metadata
        if exp_meta.get("experience_candidate", 0.0) == 0.0:
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

        # Critical missing elements from metadata and missing tech
        critical_missing_skills = comparison.skills.metadata.get("critical_missing_skills", [])
        critical_missing = critical_missing_skills + comparison.technologies.missing[:2]

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
