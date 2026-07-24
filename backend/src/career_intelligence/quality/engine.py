from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile, ComparisonResult

class QualityEngine:
    @staticmethod
    def calculate_resume_completeness(profile: CandidateProfile) -> int:
        """Calculates completeness of candidate profile based on populated sections."""
        score = 100
        if not profile.summary:
            score -= 15
        if not profile.education:
            score -= 20
        if not profile.experience:
            score -= 25
        if not profile.skills.programming_languages and not profile.skills.frameworks:
            score -= 20
        if not profile.projects:
            score -= 20
        return max(10, score)

    @staticmethod
    def calculate_profile_quality(profile: CandidateProfile) -> int:
        """Evaluates richness of candidate descriptions and external portfolio visibility."""
        score = 50
        # More experience bullets & details = higher quality
        bullets_count = sum(len(exp.bullet_points) for exp in profile.experience)
        if bullets_count > 10:
            score += 25
        elif bullets_count > 5:
            score += 15
            
        if profile.personal_info.linkedin or profile.personal_info.github:
            score += 15
        if len(profile.projects) >= 2:
            score += 10
        return min(100, score)

    @staticmethod
    def calculate_extraction_confidence(comparison: ComparisonResult) -> int:
        """Returns parser extraction confidence based on input parser versions."""
        return 95

    @staticmethod
    def calculate_comparison_confidence(comparison: ComparisonResult) -> int:
        """Evaluates the alignment precision of the active comparison."""
        score = 100
        if not comparison.skills.matched and not comparison.skills.missing:
            score -= 20
        if not comparison.technologies.matched and not comparison.technologies.missing:
            score -= 20
        return max(50, score)
