import time
from urllib.parse import urlparse
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.pipeline.fallback_models import Candidate, FailureReason

class CandidateValidator:
    def __init__(self, http_client: HttpClient):
        self.http = http_client
        
    async def validate(self, candidate: Candidate) -> bool:
        """
        Performs cheap validation on a candidate before hitting the expensive inspector.
        Returns True if it passes validation, False if it should be skipped.
        """
        parsed = urlparse(candidate.url)
        if not parsed.hostname:
            return False
            
        # For Workday, the board path must exist. 
        # A quick HEAD request to the root URL. If it's completely dead (DNS/TLS) or 404, we drop it.
        # But wait, Workday subdomains like `adobe.wd3.myworkdayjobs.com` will return 404 on root `/`
        # However, they shouldn't fail DNS/TLS. If the DNS doesn't exist, aiohttp throws ClientConnectorError.
        
        try:
            # We use a short timeout (e.g. 3 seconds) which HttpClient might support, 
            # but we can also just rely on the session timeout.
            # We fetch the actual candidate URL. For Workday, it's usually `.../cxs/...` for API, 
            # or the frontend `.../NVIDIAExternalCareerSite`.
            
            # Since Workday frontend sometimes redirects or 404s depending on the exact path,
            # a simple HEAD to the hostname itself is safer.
            root_url = f"https://{parsed.hostname}"
            
            # Using custom timeout just for validation
            # Since we can't easily override session timeout in aiohttp per-request easily without passing timeout=,
            # we'll just try to fetch.
            res = await self.http.fetch('HEAD', root_url)
            
            # If it's a valid host, it will return some HTTP status code (200, 301, 302, 401, 403, 404, etc)
            # If DNS fails or it hangs forever, it throws an exception or times out.
            # So as long as we get a response, it's a live domain.
            
            if res.status_code == 0:
                # Connection failed entirely
                return False
                
            return True
            
        except Exception as e:
            return False
