from typing import Dict, Any
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class CertificationComparer:
    @staticmethod
    def compare(profile: CandidateProfile, job: StructuredJob) -> Dict[str, Any]:
        """Compares certifications. Since JDs rarely mandate specific certs, we check for positive overrides."""
        # Check if any requirement mentions certification keywords (e.g. AWS Certified, PMP)
        req_keywords = []
        for req in job.requirements:
            if "certif" in req.name.lower():
                req_keywords.append(req.name)

        if not req_keywords:
            return {"score": 1.0, "matched": [], "reason": "No certification requirements detected in JD."}

        matched = []
        candidate_certs = {c.name.lower() for c in profile.certifications}
        
        for kw in req_keywords:
            for cert in candidate_certs:
                if cert in kw.lower() or kw.lower() in cert:
                    matched.append(cert)

        score = 1.0 if (len(matched) > 0 or not req_keywords) else 0.5
        return {
            "score": score,
            "matched": matched,
            "reason": "Certification matched." if len(matched) > 0 else "No overlapping certifications found."
        }
