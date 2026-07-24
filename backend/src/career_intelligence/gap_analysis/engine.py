from typing import List, Dict, Any, Optional
from src.career_intelligence.interfaces import AnalyzerInterface
from src.career_intelligence.models import ComparisonResult, GapAnalysis, Gap, LearningRecommendation

class GapAnalysisEngine(AnalyzerInterface):
    def analyze_gaps(self, comparison: ComparisonResult) -> GapAnalysis:
        """Transforms a ComparisonResult into prioritized, actionable career development insights."""
        critical_gaps = []
        important_gaps = []
        optional_gaps = []

        # 1. Prioritize Skills and Tech gaps
        for tech in comparison.missing_technologies:
            g = Gap(category="Technology", name=tech, priority="Critical")
            critical_gaps.append(g)

        for skill in comparison.critical_missing_skills:
            g = Gap(category="Skill", name=skill, priority="Important")
            important_gaps.append(g)

        for skill in comparison.optional_missing_skills:
            g = Gap(category="Skill", name=skill, priority="Optional")
            optional_gaps.append(g)

        # 2. Prioritize Certifications gaps
        for cert in comparison.missing_certifications:
            g = Gap(category="Certification", name=cert, priority="Optional")
            optional_gaps.append(g)

        # 3. Overall gap level
        total_gaps = len(critical_gaps) + len(important_gaps)
        if total_gaps >= 4 or comparison.experience_gap >= 3.0:
            overall_gap = "High"
        elif total_gaps >= 1 or comparison.experience_gap > 0.0:
            overall_gap = "Medium"
        else:
            overall_gap = "Low"

        # 4. Generate learning paths and recommendations
        learning_paths = []
        recommendations = []

        for tech in comparison.missing_technologies[:2]:
            learning_paths.append(LearningRecommendation(
                topic=tech,
                resource_type="project",
                description=f"Build a standalone application or module featuring {tech} integration to demonstrate capability."
            ))
            recommendations.append(f"Acquire proficiency in {tech} and showcase it in your projects block.")

        if comparison.experience_gap > 0.0:
            recommendations.append(
                f"Highlight relevant projects to compensate for the {round(comparison.experience_gap, 1)} years experience gap."
            )

        return GapAnalysis(
            overall_gap=overall_gap,
            critical_gaps=critical_gaps,
            important_gaps=important_gaps,
            optional_gaps=optional_gaps,
            missing_skills=comparison.missing_skills,
            missing_technologies=comparison.missing_technologies,
            missing_certifications=comparison.missing_certifications,
            experience_gap=comparison.experience_gap,
            education_gap=comparison.missing_degrees[0] if comparison.missing_degrees else None,
            location_gap="Relocation or remote alignment recommended" if not comparison.location_fit else None,
            strengths=comparison.strengths,
            recommendations=recommendations,
            learning_paths=learning_paths
        )
