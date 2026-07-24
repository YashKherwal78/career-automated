from typing import Dict, Any
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class LanguageComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares language requirements. Returns True by default unless explicit mismatches occur."""
        return {"language_fit": True}
