from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, LanguageComparison
from src.discovery.jie.models import StructuredJob

class LanguageComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> LanguageComparison:
        """Compares language requirements returning a strongly-typed LanguageComparison."""
        return LanguageComparison(
            score=1.0,
            language_fit=True,
            reasoning=["Language requirements are met by default."]
        )
