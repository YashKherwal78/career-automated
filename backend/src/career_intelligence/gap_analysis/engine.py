from typing import List, Dict, Any, Optional
from src.career_intelligence.interfaces import AnalyzerInterface
from src.career_intelligence.models import ComparisonResult, GapAnalysis, Gap, LearningRecommendation
from src.career_intelligence.learning.engine import LearningGraphEngine

class GapAnalysisEngine(AnalyzerInterface):
    def __init__(self):
        self.learning_engine = LearningGraphEngine()

    def analyze_gaps(self, comparison: ComparisonResult) -> GapAnalysis:
        """Transforms a ComparisonResult into prioritized, actionable career development insights."""
        critical_gaps = []
        important_gaps = []
        optional_gaps = []

        # 1. Prioritize Skills and Tech gaps
        for tech in comparison.technologies.missing:
            g = Gap(category="Technology", name=tech, priority="Critical")
            critical_gaps.append(g)

        for skill in comparison.skills.critical_missing:
            g = Gap(category="Skill", name=skill, priority="Important")
            important_gaps.append(g)

        for skill in comparison.skills.optional_missing:
            g = Gap(category="Skill", name=skill, priority="Optional")
            optional_gaps.append(g)

        # 2. Prioritize Certifications gaps
        for cert in comparison.certifications.missing:
            g = Gap(category="Certification", name=cert, priority="Optional")
            optional_gaps.append(g)

        # 3. Overall gap level
        exp_gap = comparison.experience.gap
        
        total_gaps = len(critical_gaps) + len(important_gaps)
        if total_gaps >= 4 or exp_gap >= 3.0:
            overall_gap = "High"
        elif total_gaps >= 1 or exp_gap > 0.0:
            overall_gap = "Medium"
        else:
            overall_gap = "Low"

        # 4. Generate ordered learning paths using LearningGraphEngine
        learning_paths = []
        recommendations = []

        ordered_tech_list = self.learning_engine.get_recommended_learning_order(comparison.technologies.missing)
        for tech in ordered_tech_list[:3]:
            learning_paths.append(LearningRecommendation(
                topic=tech,
                resource_type="project",
                description=f"Incorporate prerequisite technologies before building with '{tech}'."
            ))
            recommendations.append(f"Learn '{tech}' to close active tech gaps.")

        if exp_gap > 0.0:
            recommendations.append(
                f"Highlight relevant projects to compensate for the {round(exp_gap, 1)} years experience gap."
            )

        return GapAnalysis(
            overall_gap=overall_gap,
            critical_gaps=critical_gaps,
            important_gaps=important_gaps,
            optional_gaps=optional_gaps,
            missing_skills=comparison.skills.missing,
            missing_technologies=comparison.technologies.missing,
            missing_certifications=comparison.certifications.missing,
            experience_gap=exp_gap,
            education_gap=comparison.education.missing_degrees[0] if comparison.education.missing_degrees else None,
            location_gap="Relocation or remote alignment recommended" if not comparison.location.location_fit else None,
            strengths=comparison.strengths,
            recommendations=recommendations,
            learning_paths=learning_paths
        )
