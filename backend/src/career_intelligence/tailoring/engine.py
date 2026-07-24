from typing import Dict, Any, List
from src.career_intelligence.models import ComparisonResult
from src.career_intelligence.matching.engine import MatchScoreEngine

class ResumeTailoringEngine:
    def __init__(self):
        self.matcher = MatchScoreEngine()

    def generate_tailoring_plan(self, comparison: ComparisonResult) -> Dict[str, Any]:
        """Generates tailored resume suggestions entirely driven by structured ComparisonResult data."""
        match_result = self.matcher.calculate_score_from_comparison(comparison)
        
        return {
            "overall_match_score": match_result["overall_score"],
            "keyword_optimizations": [
                {
                    "type": "technology",
                    "suggestion": f"Incorporate '{tech}' into your summary or skills section.",
                    "canonical_value": tech
                } for tech in comparison.missing_technologies
            ],
            "project_prioritization": {
                "suggestions": [
                    f"Move '{proj}' to the top of your projects section because it highlights relevant stack components."
                    for proj in comparison.matched_projects
                ]
            },
            "experience_alignment": {
                "bullet_improvements": [
                    "Tailor experience descriptions to lead with achievements that highlight technology matches."
                ]
            }
        }
