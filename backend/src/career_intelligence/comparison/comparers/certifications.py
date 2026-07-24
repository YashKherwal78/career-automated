from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile, CertificationComparison
from src.discovery.jie.models import StructuredJob

class CertificationComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> CertificationComparison:
        """Compares certifications keywords between job description and candidate profile."""
        req_keywords = []
        for req in job.requirements:
            if "certif" in req.name.lower():
                req_keywords.append(req.name)

        if not req_keywords:
            return CertificationComparison(score=1.0, reasoning=["No certification requirements detected in the job description."])

        matched = []
        missing = []
        candidate_certs = {c.name.lower() for c in profile.certifications}
        
        for kw in req_keywords:
            cert_matched = False
            for cert in candidate_certs:
                if cert in kw.lower() or kw.lower() in cert:
                    matched.append(kw)
                    cert_matched = True
                    break
            if not cert_matched:
                missing.append(kw)
                
        total = len(matched) + len(missing)
        score = len(matched) / total if total > 0 else 1.0
        reasoning = [
            f"Matched {len(matched)} certifications: {', '.join(matched[:2])}."
        ]

        return CertificationComparison(
            score=score,
            matched=matched,
            missing=missing,
            reasoning=reasoning,
            confidence=0.9
        )
