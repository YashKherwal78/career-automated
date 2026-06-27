import urllib.parse
from typing import Dict, Optional

class ATSDetector:
    """
    Parses a discovered career page URL and detects the ATS provider and slug.
    """
    
    def detect_ats(self, url: str) -> Dict[str, Optional[str]]:
        result = {
            "ats_provider": "unknown",
            "slug": None,
            "original_url": url
        }
        
        url_lower = url.lower()
        
        if "boards.greenhouse.io" in url_lower:
            result["ats_provider"] = "greenhouse"
            # Ex: https://boards.greenhouse.io/browserstack
            parts = urllib.parse.urlparse(url).path.strip("/").split("/")
            if parts:
                result["slug"] = parts[0]
                
        elif "jobs.lever.co" in url_lower:
            result["ats_provider"] = "lever"
            # Ex: https://jobs.lever.co/postman
            parts = urllib.parse.urlparse(url).path.strip("/").split("/")
            if parts:
                result["slug"] = parts[0]
                
        elif "ashbyhq.com" in url_lower:
            result["ats_provider"] = "ashby"
            parts = urllib.parse.urlparse(url).path.strip("/").split("/")
            if parts:
                result["slug"] = parts[-1]
                
        return result
