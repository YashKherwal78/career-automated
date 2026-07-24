from typing import Dict, Any, List

from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.comparison.skills import SkillComparer
from src.career_intelligence.comparison.technologies import TechnologyComparer
from src.career_intelligence.comparison.experience import ExperienceComparer
from src.career_intelligence.comparison.education import EducationComparer
from src.career_intelligence.comparison.location import LocationComparer
from src.career_intelligence.comparison.employment import EmploymentComparer
from src.career_intelligence.comparison.projects import ProjectComparer

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

    def calculate_match(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Calculates configurable match scoring, strengths, gaps, and tailoring recommendations."""
        # 1. Execute individual comparers
        skills_res = SkillComparer.compare(profile, job)
        tech_res = TechnologyComparer.compare(profile, job)
        exp_res = ExperienceComparer.compare(profile, job)
        edu_res = EducationComparer.compare(profile, job)
        loc_res = LocationComparer.compare(profile, job)
        emp_res = EmploymentComparer.compare(profile, job)
        proj_res = ProjectComparer.compare(profile, job)

        # 2. Extract breakdown scores (scaled 0-100)
        breakdown = {
            "skills": int(skills_res["score"] * 100),
            "technologies": int(tech_res["score"] * 100),
            "experience": int(exp_res["score"] * 100),
            "education": int(edu_res["score"] * 100),
            "location": int(loc_res["score"] * 100),
            "employment_type": int(emp_res["score"] * 100),
            "projects": int(proj_res["score"] * 100)
        }

        # 3. Calculate weighted overall score
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

        # 4. Identify Strengths, Gaps, and Recommendations
        strengths = []
        gaps = []
        recommendations = []

        # Skills & Tech evaluation
        if breakdown["technologies"] >= 80:
            strengths.append("Strong tech stack alignment with core job technologies.")
        else:
            gaps.append(f"Missing key technologies: {', '.join(tech_res.get('missing', [])[:3])}")
            recommendations.append(f"Add projects or references showcasing: {', '.join(tech_res.get('missing', [])[:2])}")

        if breakdown["skills"] >= 80:
            strengths.append("Matches non-tech professional domain requirements.")
        else:
            gaps.append("Domain skill gaps detected.")
            recommendations.append("Incorporate standard methodology phrases (e.g. System Design, Agile) into experience bullets.")

        # Experience evaluation
        if exp_res["fit"]:
            strengths.append("Years of experience meets or exceeds job baseline.")
        else:
            gaps.append(f"Experience gap: profile shows {exp_res['candidate_years']} yrs vs required {exp_res['required_min']} yrs.")
            recommendations.append("Emphasize relevant project scope and leadership to address the experience gap.")

        # Education evaluation
        if edu_res["fit"]:
            strengths.append("Education background aligns with requirements.")
        else:
            gaps.append("Education mismatch (field of study or degree level).")
            
        return {
            "overall_score": overall_score,
            "breakdown": breakdown,
            "strengths": strengths,
            "gaps": gaps,
            "recommendations": recommendations
        }
