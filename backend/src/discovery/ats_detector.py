import re
from abc import ABC, abstractmethod
from httpx import Response
from typing import Optional

class ATSDetector(ABC):
    """Base class for detecting if an HTTP response matches a specific ATS provider."""
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """The canonical ID of the ATS provider in ats_providers."""
        pass
    
    @abstractmethod
    def detect(self, url: str, response: Response) -> bool:
        """Analyzes the response body/headers/URL to determine if it is this ATS."""
        pass
    
    @abstractmethod
    def extract_canonical_url(self, url: str, response: Response) -> str:
        """If this is the ATS, extract or format the canonical URL."""
        pass
        
    def get_confidence(self) -> int:
        """Return the confidence score of the match (0-100)."""
        return 100
        
    def get_reason(self) -> str:
        """Return the reason for the match."""
        return "Matched legacy signature"


class GreenhouseSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'greenhouse'
        
    def detect(self, url: str, response: Response) -> bool:
        if "boards.greenhouse.io" in url or "boards-api.greenhouse.io" in url or "job-boards.greenhouse.io" in url:
            if response.status_code == 200:
                return True
            # If HTML is 404, they might be API-only. Let's check the API synchronously.
            import httpx
            import re
            match = re.search(r'(?:greenhouse\.io/)([^/?]+)', url)
            if match:
                slug = match.group(1)
                try:
                    # Sync request to the API
                    api_resp = httpx.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=5.0)
                    if api_resp.status_code == 200:
                        return True
                except Exception:
                    pass
            return False
            
        if response.status_code == 200:
            if "grnhse.com" in response.text or "greenhouse.io" in response.text:
                return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        match = re.search(r'(?:boards\.greenhouse\.io/)([^/?]+)', url)
        if match:
            slug = match.group(1)
            return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        return url


class LeverSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'lever'
        
    def detect(self, url: str, response: Response) -> bool:
        if response.status_code != 200:
            return False
        if "jobs.lever.co" in url or "api.lever.co" in url:
            return True
        if "lever-jobs-logo" in response.text or "lever.co" in response.text:
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        match = re.search(r'(?:jobs\.lever\.co/|api\.lever\.co/v0/postings/)([^/?]+)', url)
        if match:
            slug = match.group(1)
            return f"https://api.lever.co/v0/postings/{slug}?mode=json"
        return url


class WorkdaySignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'workday'
        
    def detect(self, url: str, response: Response) -> bool:
        if response.status_code != 200:
            return False
        if "myworkdayjobs.com" in url:
            return True
        if "workday" in response.text.lower() and "tenant" in response.text.lower():
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url


class AshbySignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'ashby'
        
    def detect(self, url: str, response: Response) -> bool:
        if response.status_code != 200:
            return False
        if "jobs.ashbyhq.com" in url or "api.ashbyhq.com" in url:
            # Ashby returns 200 for soft 404s, verify via API
            import httpx
            import re
            match = re.search(r'(?:ashbyhq\.com/(?:posting-api/job-board/)?)([^/?]+)', url)
            if match:
                slug = match.group(1)
                if slug != 'posting-api':
                    try:
                        api_resp = httpx.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=5.0)
                        if api_resp.status_code != 200:
                            return False
                    except Exception:
                        pass
            return True
        if "ashbyhq" in response.text:
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        match = re.search(r'(?:jobs\.ashbyhq\.com/)([^/?]+)', url)
        if match:
            slug = match.group(1)
            return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        return url


class BambooHRSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'bamboohr'
        
    def detect(self, url: str, response: Response) -> bool:
        if "bamboohr.com/jobs" in url or "bamboohr.com/careers" in url:
            return True
        if "BambooHR" in response.text:
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        match = re.search(r'(?:https?://)?([^/]+)\.bamboohr\.com', url)
        if match:
            slug = match.group(1)
            return f"https://{slug}.bamboohr.com/jobs/embed2.php"
        return url

class WorkableSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'workable'
        
    def detect(self, url: str, response: Response) -> bool:
        if "apply.workable.com" in url or "workable.com" in url:
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url

class TeamtailorSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'teamtailor'
        
    def detect(self, url: str, response: Response) -> bool:
        if "teamtailor" in response.text.lower():
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url

class iCIMSSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'icims'
        
    def detect(self, url: str, response: Response) -> bool:
        if "icims.com" in url or "icims" in response.text.lower():
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url

class RecruiteeSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'recruitee'
        
    def detect(self, url: str, response: Response) -> bool:
        if "recruitee.com" in url or "recruitee" in response.text.lower():
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url

class JazzHRSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'jazzhr'
        
    def detect(self, url: str, response: Response) -> bool:
        if "applytojob.com" in url or "jazzhr" in response.text.lower():
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url

class BreezySignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'breezy'
        
    def detect(self, url: str, response: Response) -> bool:
        if "breezy.hr" in url or "breezy" in response.text.lower():
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return url

class AmazonSignature(ATSDetector):
    @property
    def provider_id(self) -> str:
        return 'amazon'
        
    def detect(self, url: str, response: Response) -> bool:
        if "amazon.jobs" in url:
            return True
        return False

    def extract_canonical_url(self, url: str, response: Response) -> str:
        return "https://www.amazon.jobs/api/jobs"
        
    def get_confidence(self) -> int:
        return 98
        
    def get_reason(self) -> str:
        return "amazon.jobs domain matched"

class DetectorRegistry:
    """Central registry of ATS detectors."""
    _detectors = [
        GreenhouseSignature(),
        LeverSignature(),
        WorkdaySignature(),
        AshbySignature(),
        BambooHRSignature(),
        WorkableSignature(),
        TeamtailorSignature(),
        iCIMSSignature(),
        RecruiteeSignature(),
        JazzHRSignature(),
        BreezySignature(),
        AmazonSignature()
    ]
    
    @classmethod
    def detect_all(cls, url: str, response: Response) -> Optional[ATSDetector]:
        """Returns the first matching ATSDetector."""
        for detector in cls._detectors:
            if detector.detect(url, response):
                return detector
        return None
