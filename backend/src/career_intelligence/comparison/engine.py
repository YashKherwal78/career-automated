import datetime
from typing import Dict, Any

from src.career_intelligence.models import CandidateProfile, ComparisonResult, ComparisonContext
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

        # Build strengths and weaknesses from structured sub-comparisons
        strengths = []
        weaknesses = []

        if techs.score >= 0.8:
            strengths.append("Strong tech stack alignment with core job technologies.")
        if techs.missing:
            weaknesses.append(f"Missing technology keywords: {', '.join(techs.missing[:3])}")

        if exp.score == 1.0:
            strengths.append("Meets or exceeds minimum years of experience requirement.")
        elif exp.gap > 0:
            weaknesses.append(f"Experience gap of {exp.gap} years.")

        # Build auditing context metadata
        context = ComparisonContext(
            parser_version="2.0.0",
            ontology_version="1.0.0",
            weight_profile="Default",
            comparison_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            comparison_algorithm_version="3.0.0",
            feature_flags={"use_career_ontology": True}
        )

        return ComparisonResult(
            candidate_id=getattr(profile, "candidate_id", None),
            job_id=getattr(job, "job_id", None),
            generated_at=context.comparison_timestamp,
            profile_version="2.0.0",
            job_version="3.0.0",
            
            context=context,
            skills=skills,
            technologies=techs,
            education=edu,
            experience=exp,
            projects=proj,
            certifications=certs,
            location=loc,
            employment=emp,
            responsibilities=resps,
            languages=langs,
            
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=[],
            metadata={}
        )
