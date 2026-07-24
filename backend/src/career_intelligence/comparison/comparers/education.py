from typing import Dict, Any
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class EducationComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares candidate academic degrees and fields of study against job specifications."""
        if not job.education:
            return {
                "education_fit": True,
                "matched_degrees": [],
                "missing_degrees": []
            }

        # Candidate degrees and fields
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
            # Check overlap against degrees or fields
            if req.lower() in candidate_degrees or req.lower() in candidate_fields:
                matched_deg.append(req)
            else:
                missing_deg.append(req)

        # Simple fitness evaluation
        education_fit = len(matched_deg) > 0
        return {
            "education_fit": education_fit,
            "matched_degrees": matched_deg,
            "missing_degrees": missing_deg
        }
