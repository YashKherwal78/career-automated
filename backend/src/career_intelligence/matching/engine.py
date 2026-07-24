from typing import Dict, Any
from src.career_intelligence.models import ComparisonResult

DEFAULT_WEIGHTS = {
    "skills": 0.20,
    "technologies": 0.25,
    "experience": 0.20,
    "education": 0.15,
    "location": 0.10,
    "employment_type": 0.05,
    "projects": 0.05
}

class MatchScoreEngine:
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def calculate_score_from_comparison(self, comparison: ComparisonResult) -> Dict[str, Any]:
        """Calculates configurable match scoring and recommendations directly from a ComparisonResult."""
        # Calculate component ratios from matched / total items
        total_skills = len(comparison.matched_skills) + len(comparison.missing_skills)
        skills_score = len(comparison.matched_skills) / total_skills if total_skills > 0 else 1.0

        total_techs = len(comparison.matched_technologies) + len(comparison.missing_technologies)
        tech_score = len(comparison.matched_technologies) / total_techs if total_techs > 0 else 1.0

        exp_score = 1.0 if comparison.experience_gap is None else max(0.0, 1.0 - (comparison.experience_gap / 10.0))
        edu_score = 1.0 if comparison.education_fit else 0.0
        loc_score = 1.0 if (comparison.location_fit or comparison.work_mode_fit) else 0.0
        
        # Build breakdown dictionary (scaled 0-100)
        breakdown = {
            "skills": int(skills_score * 100),
            "technologies": int(tech_score * 100),
            "experience": int(exp_score * 100),
            "education": int(edu_score * 100),
            "location": int(loc_score * 100),
            "employment_type": 100, # Default fit fallback
            "projects": 100 if comparison.matched_projects else 50
        }

        # Calculate weighted overall score
        overall_score = 0.0
        total_weight = 0.0
        for category, score_val in breakdown.items():
            weight = self.weights.get(category, 0.0)
            overall_score += (score_val * weight)
            total_weight += weight

        if total_weight > 0:
            overall_score = int(overall_score / total_weight)
        else:
            overall_score = 100

        # Build list of user suggestions
        recommendations = []
        if comparison.missing_technologies:
            recommendations.append(f"Add projects or references showcasing: {', '.join(comparison.missing_technologies[:2])}")
        if comparison.missing_skills:
            recommendations.append(f"Incorporate professional methodologies like: {', '.join(comparison.missing_skills[:2])}")
        if comparison.experience_gap:
            recommendations.append("Emphasize relevant project scope and leadership to address the experience gap.")

        return {
            "overall_score": overall_score,
            "breakdown": breakdown,
            "strengths": comparison.strengths,
            "gaps": comparison.weaknesses,
            "recommendations": recommendations
        }
