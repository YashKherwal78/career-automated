from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class EducationComparer:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares candidate education degrees and fields against job specifications."""
        if not job.education:
            return {
                "score": 1.0,
                "fit": True,
                "matched": [],
                "reason": "No education requirements specified by the job description."
            }

        # Gather candidate degrees & fields
        candidate_edu = set()
        for edu in profile.education:
            if edu.degree:
                candidate_edu.add(edu.degree.lower())
            if edu.field_of_study:
                candidate_edu.add(edu.field_of_study.lower())

        matched = []
        missing = []
        for edu_req in job.education:
            if edu_req.lower() in candidate_edu:
                matched.append(edu_req)
            else:
                missing.append(edu_req)

        # Fit is true if there's any degree/field overlap
        fit = len(matched) > 0
        score = 1.0 if fit else 0.0
        reason = (
            f"Candidate credentials overlap with: {', '.join(matched)}"
            if fit else "Candidate credentials do not match requirements."
        )

        return {
            "score": score,
            "fit": fit,
            "matched": matched,
            "missing": missing,
            "reason": reason
        }
