import requests
import re
import time
from typing import Dict, Optional

class ATSDetector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def _slugify(self, text: str) -> str:
        text = str(text).lower()
        return re.sub(r'[^a-z0-9]', '', text)

    def _slug_variants(self, company_name: str) -> list:
        base = self._slugify(company_name)
        variants = [
            base,
            base.replace("india", "").replace("inc", "").replace("pvt", "").replace("ltd", ""),
            f"{base}hq",
            f"{base}inc"
        ]
        # deduplicate while preserving order
        seen = set()
        return [x for x in variants if not (x in seen or seen.add(x)) and len(x) > 1]

    def check_greenhouse(self, slug: str) -> bool:
        try:
            r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}", timeout=3, headers=self.headers)
            return r.status_code == 200
        except: return False

    def check_lever(self, slug: str) -> bool:
        try:
            r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=3, headers=self.headers)
            return r.status_code == 200
        except: return False

    def check_ashby(self, slug: str) -> bool:
        try:
            r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=3, headers=self.headers)
            return r.status_code == 200
        except: return False

    def detect_ats(self, company_name: str) -> Dict[str, Optional[str]]:
        """
        Attempts to detect the ATS provider and slug for a given company.
        """
        variants = self._slug_variants(company_name)
        
        for slug in variants:
            if self.check_greenhouse(slug):
                return {"provider": "greenhouse", "slug": slug, "base_url": None, "method": "api_ping"}
            
            if self.check_lever(slug):
                return {"provider": "lever", "slug": slug, "base_url": None, "method": "api_ping"}
                
            if self.check_ashby(slug):
                return {"provider": "ashby", "slug": slug, "base_url": None, "method": "api_ping"}
                
        return {"provider": None, "slug": None, "base_url": None, "method": "failed"}

# Standalone execution for testing
if __name__ == "__main__":
    detector = ATSDetector()
    print(detector.detect_ats("Rippling"))
