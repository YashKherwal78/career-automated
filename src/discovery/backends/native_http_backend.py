from typing import Dict, Any
from datetime import datetime
from src.discovery.backends.base_backend import BaseBackend
from src.discovery.backends.rate_limiter import RateLimiter

class NativeHTTPBackend(BaseBackend):
    def __init__(self):
        self.rate_limiter = RateLimiter()

    def fetch(self, query: str, location: str, **kwargs) -> Dict[str, Any]:
        """
        Mock implementation of Native HTTP backend.
        Wrapped in the rate limiter for safety.
        """
        def _execute():
            # Mock actual HTTP request logic here
            return {
                "results": [
                    {
                        "company": "NewAge AI",
                        "role": query,
                        "location": location,
                        "remote": "Remote",
                        "experience": "0-2 Years",
                        "description": "Build GenAI models.",
                        "url": f"https://example.com/viewjob?q={query}",
                        "website": "https://jobs.lever.co/newageai",
                        "date_posted": datetime.utcnow().isoformat()
                    }
                ],
                "meta": {
                    "latency_ms": 120,
                    "status_code": 200
                }
            }
            
        return self.rate_limiter.execute(_execute)
