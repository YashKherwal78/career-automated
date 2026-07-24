from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, EmploymentComparison
from src.discovery.jie.models import StructuredJob

class EmploymentComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> EmploymentComparison:
        """Compares job employment types returning a strongly-typed EmploymentComparison."""
        if job.employment_type == "Unknown":
            return EmploymentComparison(score=1.0, employment_type_fit=True, reasoning=["No strict employment formats required."])

        candidate_pref_types = set()
        for exp in profile.experience:
            if exp.employment_type:
                candidate_pref_types.add(exp.employment_type.lower())
                
        fit = len(candidate_pref_types) == 0 or job.employment_type.lower() in candidate_pref_types
        score = 1.0 if fit else 0.5
        reasoning = [
            f"Job employment format: {job.employment_type}.",
            f"Candidate preferences matching: {fit}."
        ]

        return EmploymentComparison(
            score=score,
            employment_type_fit=fit,
            reasoning=reasoning,
            confidence=0.9
        )
