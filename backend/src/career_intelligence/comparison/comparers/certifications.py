from typing import Dict, Any, List
from src.career_intelligence.interfaces import ComparerInterface
from src.career_intelligence.models import CandidateProfile
from src.discovery.jie.models import StructuredJob

class CertificationComparer(ComparerInterface):
    def compare(self, profile: CandidateProfile, job: StructuredJob) -> Dict[str, List[str]]:
        """Compares certifications keywords between job description and candidate profile."""
        req_keywords = []
        for req in job.requirements:
            if "certif" in req.name.lower():
                req_keywords.append(req.name)

        if not req_keywords:
            return {"certifications_matched": [], "certifications_missing": []}

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
                
        return {
            "certifications_matched": matched,
            "certifications_missing": missing
        }
