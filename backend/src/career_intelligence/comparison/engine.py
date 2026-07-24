from typing import Dict, Any, List

from src.career_intelligence.models import CandidateProfile, ComparisonResult
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.comparison.skills import SkillComparer
from src.career_intelligence.comparison.technologies import TechnologyComparer
from src.career_intelligence.comparison.experience import ExperienceComparer
from src.career_intelligence.comparison.education import EducationComparer
from src.career_intelligence.comparison.location import LocationComparer
from src.career_intelligence.comparison.employment import EmploymentComparer
from src.career_intelligence.comparison.projects import ProjectComparer
from src.career_intelligence.comparison.certifications import CertificationComparer

class CareerComparisonEngine:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> ComparisonResult:
        """Executes full structured comparison and returns a unified ComparisonResult."""
        skills_res = SkillComparer.compare(profile, job)
        tech_res = TechnologyComparer.compare(profile, job)
        exp_res = ExperienceComparer.compare(profile, job)
        edu_res = EducationComparer.compare(profile, job)
        loc_res = LocationComparer.compare(profile, job)
        emp_res = EmploymentComparer.compare(profile, job)
        proj_res = ProjectComparer.compare(profile, job)
        cert_res = CertificationComparer.compare(profile, job)

        # Calculate experience gap
        required_min = exp_res.get("required_min") or 0
        cand_years = exp_res.get("candidate_years") or 0.0
        exp_gap = max(0.0, required_min - cand_years) if required_min > cand_years else None

        # Build list of missing experiences
        missing_exp = []
        if exp_gap:
            missing_exp.append(f"Missing {round(exp_gap, 1)} years of required domain experience.")

        # Aggregate strengths & weaknesses
        strengths = []
        weaknesses = []

        if len(tech_res.get("matched", [])) >= 2:
            strengths.append("Matches core required technologies.")
        if len(tech_res.get("missing", [])) > 0:
            weaknesses.append(f"Missing technology keywords: {', '.join(tech_res['missing'][:3])}")

        if len(skills_res.get("matched", [])) >= 1:
            strengths.append("Possesses relevant professional domain skills.")
        if len(skills_res.get("missing", [])) > 0:
            weaknesses.append(f"Missing professional skills: {', '.join(skills_res['missing'][:3])}")

        if exp_res.get("fit"):
            strengths.append("Meets minimum years of experience requirement.")
        elif exp_gap:
            weaknesses.append(f"Has experience gap of {round(exp_gap, 1)} years.")

        if edu_res.get("fit"):
            strengths.append("Education background aligns with job expectations.")

        return ComparisonResult(
            matched_skills=skills_res.get("matched", []),
            missing_skills=skills_res.get("missing", []),
            
            matched_technologies=tech_res.get("matched", []),
            missing_technologies=tech_res.get("missing", []),
            
            matched_projects=[p["name"] for p in proj_res.get("matched_projects", [])],
            relevant_projects=[p["name"] for p in proj_res.get("matched_projects", [])],
            
            missing_experience=missing_exp,
            experience_gap=exp_gap,
            
            education_fit=edu_res.get("fit", False),
            location_fit=loc_res.get("city_match", False) or loc_res.get("country_match", False),
            work_mode_fit=loc_res.get("work_mode_compatible", False),
            
            certifications_matched=cert_res.get("matched", []),
            certifications_missing=cert_res.get("missing", []),
            
            responsibilities_overlap=[],
            strengths=strengths,
            weaknesses=weaknesses
        )
