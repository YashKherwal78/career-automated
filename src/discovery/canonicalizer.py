import hashlib
import re
from typing import Dict, Any, Optional

class JobCanonicalizer:
    """
    Normalizes messy job data and generates deterministic fingerprints for deduplication.
    """
    
    # Trust scores for deduplication tie-breaking
    SOURCE_TRUST_SCORES = {
        "greenhouse": 100,
        "lever": 100,
        "ashby": 98,
        "workable": 95,
        "smartrecruiters": 95,
        "company_careers": 100,
        "linkedin": 90,
        "indeed": 70,
        "apify": 60,
        "unknown": 50
    }
    
    def __init__(self):
        pass
        
    def _normalize_title(self, title: str) -> str:
        """
        Lowercases, strips punctuation, and normalizes common title variations.
        e.g., 'Software Engineer II' -> 'software engineer ii'
        """
        if not title:
            return "unknown"
            
        t = title.lower().strip()
        # Remove common trailing artifacts
        t = re.sub(r'[\(\[\-].*?[\)\]]', '', t)  # Remove (Remote) or - London
        t = re.sub(r'[^a-z0-9\s]', '', t)        # Strip punctuation
        t = re.sub(r'\s+', ' ', t).strip()       # Normalize whitespace
        
        # Normalize common abbreviations
        t = re.sub(r'\bswe\b', 'software engineer', t)
        t = re.sub(r'\bml\b', 'machine learning', t)
        t = re.sub(r'\bqa\b', 'quality assurance', t)
        
        return t
        
    def _normalize_location(self, location: str) -> str:
        """
        Normalizes location string, prioritizing 'remote' if present.
        """
        if not location:
            return "unknown"
            
        l = location.lower().strip()
        if "remote" in l or "anywhere" in l:
            return "remote"
            
        # Strip specific trailing/leading junk if needed
        l = re.sub(r'[^a-z0-9\s\,]', '', l)
        l = re.sub(r'\s+', ' ', l).strip()
        return l
        
    def _normalize_employment_type(self, emp_type: str) -> str:
        if not emp_type:
            return "full-time" # Default
            
        e = emp_type.lower().strip()
        if "contract" in e: return "contract"
        if "intern" in e: return "internship"
        if "part" in e: return "part-time"
        return "full-time"

    def canonicalize(self, raw_job: Dict[str, Any], company_id: str) -> Dict[str, Any]:
        """
        Takes a raw scraped job and returns a normalized payload with fingerprint.
        """
        canonical = dict(raw_job) # Shallow copy
        
        # 1. Normalize Core Fields
        canonical["normalized_title"] = self._normalize_title(raw_job.get("title", ""))
        canonical["normalized_location"] = self._normalize_location(raw_job.get("location", ""))
        canonical["normalized_employment_type"] = self._normalize_employment_type(raw_job.get("employment_type", ""))
        canonical["company_id"] = company_id
        
        # 2. Generate Fingerprint
        # hash(company_id, normalized_title, normalized_location, employment_type)
        fingerprint_string = f"{company_id}|{canonical['normalized_title']}|{canonical['normalized_location']}|{canonical['normalized_employment_type']}"
        canonical["fingerprint"] = hashlib.sha256(fingerprint_string.encode('utf-8')).hexdigest()
        
        # 3. Attach Source Trust Score
        provider = str(raw_job.get("provider", "unknown")).lower()
        canonical["source_trust_score"] = self.SOURCE_TRUST_SCORES.get(provider, 50)
        
        # 4. Generate Quality Score (0-100)
        quality = 100
        if not raw_job.get("description"): quality -= 40
        if not raw_job.get("apply_url"): quality -= 30
        if not raw_job.get("salary_min"): quality -= 10
        canonical["payload_quality_score"] = max(0, quality)
        
        return canonical
