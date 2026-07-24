import datetime
from typing import Dict, Any

from src.career_intelligence.models import CandidateProfile, ComparisonResult
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
        """Executes domain comparisons exactly once to return a comprehensive ComparisonResult."""
        skills = self.skill_comparer.compare(profile, job)
        techs = self.tech_comparer.compare(profile, job)
        exp = self.exp_comparer.compare(profile, job)
        edu = self.edu_comparer.compare(profile, job)
        loc = self.loc_comparer.compare(profile, job)
        emp = self.emp_comparer.compare(profile, job)
        proj = self.proj_comparer.compare(profile, job)
        certs = self.cert_comparer.compare(profile, job)
        resps = self.resp_comparer.compare(profile, job)
        langs = self.lang_comparer.compare(profile, job)

        # Reconcile strengths and weaknesses
        strengths = []
        weaknesses = []

        if len(techs["matched"]) >= 2:
            strengths.append("Strong tech stack alignment with core job technologies.")
        if len(techs["missing"]) > 0:
            weaknesses.append(f"Missing technology keywords: {', '.join(techs['missing'][:3])}")

        if len(skills["matched"]) >= 1:
            strengths.append("Matches core required professional domain skills.")

        if exp["experience_fit"]:
            strengths.append("Meets or exceeds minimum years of experience requirement.")
        elif exp["experience_gap"] > 0:
            weaknesses.append(f"Experience gap of {exp['experience_gap']} years.")

        if edu["education_fit"]:
            strengths.append("Education credentials match requirements.")

        return ComparisonResult(
            candidate_id=getattr(profile, "candidate_id", None),
            job_id=getattr(job, "job_id", None),
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            profile_version="2.0.0",
            job_version="3.0.0",
            
            matched_skills=skills["matched"],
            missing_skills=skills["missing"],
            extra_skills=skills["extra"],
            critical_missing_skills=skills["critical_missing"],
            optional_missing_skills=skills["optional_missing"],
            
            matched_technologies=techs["matched"],
            missing_technologies=techs["missing"],
            extra_technologies=techs["extra"],
            technology_categories=techs["categories"],
            
            matched_projects=proj["matched_projects"],
            relevant_projects=proj["relevant_projects"],
            irrelevant_projects=proj["irrelevant_projects"],
            
            matched_certifications=certs["certifications_matched"],
            missing_certifications=certs["certifications_missing"],
            
            education_fit=edu["education_fit"],
            matched_degrees=edu["matched_degrees"],
            missing_degrees=edu["missing_degrees"],
            
            experience_required=exp["experience_required"],
            experience_candidate=exp["experience_candidate"],
            experience_gap=exp["experience_gap"],
            experience_fit=exp["experience_fit"],
            
            location_fit=loc["location_fit"],
            work_mode_fit=loc["work_mode_fit"],
            employment_type_fit=emp["employment_type_fit"],
            language_fit=langs["language_fit"],
            
            responsibility_matches=resps["responsibility_matches"],
            responsibility_gaps=resps["responsibility_gaps"],
            
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=[],
            metadata={}
        )
