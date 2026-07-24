from typing import List, Dict, Any, Optional
from src.career_intelligence.interfaces import AnalyzerInterface
from src.career_intelligence.models import ComparisonResult, GapAnalysis, Gap, LearningRecommendation

class GapAnalysisEngine(AnalyzerInterface):
    def analyze_gaps(self, comparison: ComparisonResult) -> GapAnalysis:
        """Transforms a ComparisonResult into prioritized, actionable career development insights."""
        critical_gaps = []
        important_gaps = []
        optional_gaps = []

        # 1. Prioritize Skills and Tech gaps from hierarchical metadata
        for tech in comparison.technologies.missing:
            g = Gap(category="Technology", name=tech, priority="Critical")
            critical_gaps.append(g)

        critical_missing_skills = comparison.skills.metadata.get("critical_missing_skills", [])
        for skill in critical_missing_skills:
            g = Gap(category="Skill", name=skill, priority="Important")
            important_gaps.append(g)

        optional_missing_skills = comparison.skills.metadata.get("optional_missing_skills", [])
        for skill in optional_missing_skills:
            g = Gap(category="Skill", name=skill, priority="Optional")
            optional_gaps.append(g)

        # 2. Prioritize Certifications gaps
        for cert in comparison.certifications.missing:
            g = Gap(category="Certification", name=cert, priority="Optional")
            optional_gaps.append(g)

        # 3. Overall gap level
        exp_gap = comparison.experience.metadata.get("experience_gap", 0.0)
        total_gaps = len(critical_gaps) + len(important_gaps)
        if total_gaps >= 4 or exp_gap >= 3.0:
            overall_gap = "High"
        elif total_gaps >= 1 or exp_gap > 0.0:
            overall_gap = "Medium"
        else:
            overall_gap = "Low"

        # 4. Generate learning paths and recommendations
        learning_paths = []
        recommendations = []

        for tech in comparison.technologies.missing[:2]:
            learning_paths.append(LearningRecommendation(
                topic=tech,
                resource_type="project",
                description=f"Build a standalone application or module featuring {tech} integration to demonstrate capability."
            ))
            recommendations.append(f"Acquire proficiency in {tech} and showcase it in your projects block.")

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
            education_gap=comparison.education.missing[0] if comparison.education.missing else None,
            location_gap="Relocation or remote alignment recommended" if not comparison.location.metadata.get("location_fit") else None,
            strengths=comparison.strengths,
            recommendations=recommendations,
            learning_paths=learning_paths
        )
