import datetime
from typing import Dict, Any

from src.career_intelligence.models import CandidateProfile, ComparisonResult, SubComparison
from src.discovery.jie.models import StructuredJob
from src.career_intelligence.comparison.comparers.skills import SkillComparer
from src.career_intelligence.comparison.comparers.technologies import TechnologyComparer
from src.career_intelligence.comparison.comparers.experience import ExperienceComparer
from src.career_intelligence.comparison.comparers.education import EducationComparer
from src.career_intelligence.comparison.comparers.location import LocationComparer
from src.career_intelligence.comparison.comparers.employment import EmploymentComparer
from src.career_intelligence.comparison.comparers.projects import ProjectComparer
from src.career_intelligence.comparison.comparers.certifications import CertificationComparer
from src.career_intelligence.comparison.comparers.responsibilities import ResponsibilityComparer
from src.career_intelligence.comparison.comparers.languages import LanguageComparer

class CareerComparisonEngine:
    def __init__(self):
        self.skill_comparer = SkillComparer()
        self.tech_comparer = TechnologyComparer()
        self.exp_comparer = ExperienceComparer()
        self.edu_comparer = EducationComparer()
        self.loc_comparer = LocationComparer()
        self.emp_comparer = EmploymentComparer()
        self.proj_comparer = ProjectComparer()
        self.cert_comparer = CertificationComparer()
        self.resp_comparer = ResponsibilityComparer()
        self.lang_comparer = LanguageComparer()

    def compare(self, profile: CandidateProfile, job: StructuredJob) -> ComparisonResult:
        """Executes domain comparisons exactly once to return a hierarchical ComparisonResult."""
        skills_res = self.skill_comparer.compare(profile, job)
        techs_res = self.tech_comparer.compare(profile, job)
        exp_res = self.exp_comparer.compare(profile, job)
        edu_res = self.edu_comparer.compare(profile, job)
        loc_res = self.loc_comparer.compare(profile, job)
        emp_res = self.emp_comparer.compare(profile, job)
        proj_res = self.proj_comparer.compare(profile, job)
        certs_res = self.cert_comparer.compare(profile, job)
        resps_res = self.resp_comparer.compare(profile, job)
        langs_res = self.lang_comparer.compare(profile, job)

        # 1. Map to hierarchical SubComparison objects
        def get_ratio_score(matched, missing):
            total = len(matched) + len(missing)
            return len(matched) / total if total > 0 else 1.0

        skills_sub = SubComparison(
            score=get_ratio_score(skills_res["matched"], skills_res["missing"]),
            matched=skills_res["matched"],
            missing=skills_res["missing"],
            reasoning=f"Matches {len(skills_res['matched'])} out of {len(skills_res['matched']) + len(skills_res['missing'])} skills.",
            metadata={
                "extra_skills": skills_res["extra"],
                "critical_missing_skills": skills_res["critical_missing"],
                "optional_missing_skills": skills_res["optional_missing"]
            }
        )

        techs_sub = SubComparison(
            score=get_ratio_score(techs_res["matched"], techs_res["missing"]),
            matched=techs_res["matched"],
            missing=techs_res["missing"],
            reasoning=f"Matches {len(techs_res['matched'])} out of {len(techs_res['matched']) + len(techs_res['missing'])} tech skills.",
            metadata={
                "extra_technologies": techs_res["extra"],
                "technology_categories": techs_res["categories"]
            }
        )

        exp_gap = exp_res["experience_gap"]
        exp_sub = SubComparison(
            score=1.0 if exp_res["experience_fit"] else max(0.0, 1.0 - (exp_gap / 10.0)),
            matched=[],
            missing=[f"Missing {round(exp_gap, 1)} years of experience"] if exp_gap > 0 else [],
            reasoning=f"Candidate experience: {exp_res['experience_candidate']} yrs vs required: {exp_res['experience_required']} yrs.",
            metadata={
                "experience_required": exp_res["experience_required"],
                "experience_candidate": exp_res["experience_candidate"],
                "experience_gap": exp_gap,
                "experience_fit": exp_res["experience_fit"]
            }
        )

        edu_sub = SubComparison(
            score=1.0 if edu_res["education_fit"] else 0.0,
            matched=edu_res["matched_degrees"],
            missing=edu_res["missing_degrees"],
            reasoning="Required degree level or field matches candidate credentials." if edu_res["education_fit"] else "Academic qualifications do not match requirements.",
            metadata={
                "education_fit": edu_res["education_fit"]
            }
        )

        loc_sub = SubComparison(
            score=1.0 if (loc_res["location_fit"] and loc_res["work_mode_fit"]) else 0.5,
            reasoning="Location alignment or compatible work mode preferences.",
            metadata=loc_res
        )

        emp_sub = SubComparison(
            score=1.0 if emp_res["employment_type_fit"] else 0.5,
            reasoning="Employment format (Full-time/Contract) is compatible.",
            metadata=emp_res
        )

        proj_sub = SubComparison(
            score=get_ratio_score(proj_res["matched_projects"], proj_res["irrelevant_projects"]),
            matched=proj_res["matched_projects"],
            missing=[],
            reasoning=f"Candidate possesses {len(proj_res['matched_projects'])} relevant projects matching tech stack.",
            metadata=proj_res
        )

        certs_sub = SubComparison(
            score=get_ratio_score(certs_res["certifications_matched"], certs_res["certifications_missing"]),
            matched=certs_res["certifications_matched"],
            missing=certs_res["certifications_missing"],
            reasoning=f"Certification match evaluation completes with {len(certs_res['certifications_matched'])} matches."
        )

        resps_sub = SubComparison(
            score=get_ratio_score(resps_res["responsibility_matches"], resps_res["responsibility_gaps"]),
            matched=resps_res["responsibility_matches"],
            missing=resps_res["responsibility_gaps"],
            reasoning=f"Matches {len(resps_res['responsibility_matches'])} job responsibilities."
        )

        langs_sub = SubComparison(
            score=1.0 if langs_res["language_fit"] else 0.0,
            reasoning="Language proficiency requirements are compatible."
        )

        # 2. Extract strengths and weaknesses
        strengths = []
        weaknesses = []

        if techs_sub.score >= 0.8:
            strengths.append("Strong tech stack alignment with core job technologies.")
        if techs_sub.missing:
            weaknesses.append(f"Missing technology keywords: {', '.join(techs_sub.missing[:3])}")

        if exp_sub.score == 1.0:
            strengths.append("Meets or exceeds minimum years of experience requirement.")
        elif exp_gap > 0:
            weaknesses.append(f"Experience gap of {exp_gap} years.")

        return ComparisonResult(
            candidate_id=getattr(profile, "candidate_id", None),
            job_id=getattr(job, "job_id", None),
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            profile_version="2.0.0",
            job_version="2.0.0",
            
            skills=skills_sub,
            technologies=techs_sub,
            education=edu_sub,
            experience=exp_sub,
            projects=proj_sub,
            certifications=certs_sub,
            location=loc_sub,
            employment=emp_sub,
            responsibilities=resps_sub,
            languages=langs_sub,
            
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=[],
            metadata={}
        )
