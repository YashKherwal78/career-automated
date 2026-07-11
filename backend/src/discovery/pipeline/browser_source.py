import os
import time
import logging
from urllib.parse import urlparse
from typing import List, Optional
from playwright.async_api import async_playwright
from src.discovery.pipeline.fallback_models import DiscoverySource, SourceResult, StageTrace, Candidate, Evidence, ProbeResult
from src.discovery.pipeline.discovery_orchestrator import DiscoveryContext

logger = logging.getLogger("BrowserSearchSource")

class BrowserSearchSource(DiscoverySource):
    """
    Fallback discovery mechanism using a secondary Exa search strategy.
    (Replaces local Playwright due to Google Captcha blocks in dev).
    Uses strict ATS domain filtering.
    """
    async def discover(self, context: DiscoveryContext) -> SourceResult:
        start_time = time.time()
        candidates = []
        probe_results = []
        error_msg = None
        
        from src.common.credential_provider import CredentialFactory, Credential, RateLimitException, AuthException
        credentials = CredentialFactory.get("EXA")
        
        try:
            payload = {
                "query": context.company,
                "numResults": 5,
                "useAutoprompt": False,
                "includeDomains": context.ats_domains if context.ats_domains else ["myworkdayjobs.com", "greenhouse.io", "lever.co"]
            }
            
            probe_start = time.time()
            
            async def fetch(credential: Credential):
                headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "x-api-key": credential.secret
                }
                res = await context.http.fetch('POST', 'https://api.exa.ai/search', headers=headers, json=payload)
                if res.status_code == 429:
                    raise RateLimitException()
                elif res.status_code in [401, 403]:
                    raise AuthException()
                return res

            res = await credentials.execute(fetch)
            
            probe_results.append(ProbeResult(
                path="https://api.exa.ai/search",
                status=res.status_code,
                final_url="https://api.exa.ai/search",
                latency_ms=int((time.time() - probe_start)*1000),
                redirect_count=0,
                success=res.status_code == 200
            ))
            
            if res.status_code == 200:
                if isinstance(res.payload, dict):
                    data = res.payload
                else:
                    import json
                    data = json.loads(res.payload.decode('utf-8'))
                    
                results = data.get("results", [])
                
                for r in results:
                    url = r.get("url")
                    if url:
                        c = Candidate(url=url)
                        c.search_provider = "ExaFallback"
                        c.search_query = context.company
                        c.search_rank = results.index(r) + 1
                        c.search_title = r.get("title", "")
                        
                        c.evidence.append(Evidence(
                            source="BrowserSearchSource(ExaFallback)", 
                            weight=40, 
                            description=f"Found via Fallback Exa (Domain filter)"
                        ))
                        candidates.append(c)
            else:
                error_msg = f"Exa fallback returned status {res.status_code}"
                        
        except Exception as e:
            error_msg = str(e)
            
        trace = StageTrace(
            stage="browser_fallback",
            success=error_msg is None,
            duration_ms=int((time.time() - start_time) * 1000),
            requests=context.requests_used,
            candidates_found=len(candidates),
            evidence=[],
            urls=[c.url for c in candidates],
            probe_results=probe_results,
            redirect_chains=[],
            error=error_msg
        )
        
        return SourceResult(candidates=candidates, trace=trace, requests_used=1, bytes_downloaded=0)
