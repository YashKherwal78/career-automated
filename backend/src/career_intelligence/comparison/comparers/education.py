from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, EducationComparison
from src.discovery.jie.models import StructuredJob

class EducationComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> EducationComparison:
        """Compares academic credentials against job requirements returning an EducationComparison."""
        if not job.education:
            return EducationComparison(score=1.0, fit=True, reasoning=["No education requirements specified by the job."])

        candidate_degrees = set()
        candidate_fields = set()
        for edu in profile.education:
            if edu.degree:
                candidate_degrees.add(edu.degree.lower())
            if edu.field_of_study:
                candidate_fields.add(edu.field_of_study.lower())

        matched_deg = []
        missing_deg = []
        for req in job.education:
            if req.lower() in candidate_degrees or req.lower() in candidate_fields:
                matched_deg.append(req)
            else:
                missing_deg.append(req)

        fit = len(matched_deg) > 0
        score = 1.0 if fit else 0.0
        reasoning = [
            f"Matched degree or field: {', '.join(matched_deg)}" if fit else "Education credentials do not match requirements."
        ]

        return EducationComparison(
            score=score,
            required_degree=job.education,
            candidate_degree=list(candidate_degrees),
            missing_degrees=missing_deg,
            degree_equivalent=fit,
            field_equivalent=fit,
            fit=fit,
            reasoning=reasoning,
            confidence=0.9
        )
