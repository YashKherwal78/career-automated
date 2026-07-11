from typing import List, Optional, Tuple, Any
from src.discovery.pipeline.fallback_models import DiscoveryPlugin
from src.discovery.models import BoardIdentity
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.inspectors.greenhouse_inspector import GreenhouseInspector
from src.discovery.pipeline.parsers import GreenhouseParser

class GreenhouseDiscoveryPlugin(DiscoveryPlugin):
    def __init__(self):
        self.parser = GreenhouseParser()

    @property
    def provider_name(self) -> str:
        return "greenhouse"
        
    def candidate_domains(self) -> List[str]:
        return ["boards.greenhouse.io", "boards.eu.greenhouse.io", "greenhouse.io"]
        
    def fingerprints(self) -> List[str]:
        return [
            "greenhouse.io"
        ]
        
    def parse_candidate(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        return self.parser.parse(url)
        
    def inspector(self) -> SourceInspector:
        return GreenhouseInspector()
        
    def confidence(self, evidence: Any) -> float:
        return 1.0

    def canonicalize(self, endpoint: str) -> str:
        """
        Normalize a Greenhouse URL to the board-level URL.

        Input examples:
          https://boards.greenhouse.io/figma/jobs/5691911004
          https://boards.greenhouse.io/figma/jobs
          https://boards.greenhouse.io/figma?gh_jid=123
        Output:
          https://boards.greenhouse.io/figma
        """
        import re
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(endpoint)
        path = parsed.path.rstrip('/')
        # Strip /jobs/{numeric_id} or /jobs/{numeric_id}/... (job-level paths)
        path = re.sub(r'/jobs/\d+.*$', '', path, flags=re.IGNORECASE)
        # Strip bare /jobs suffix
        path = re.sub(r'/jobs$', '', path, flags=re.IGNORECASE)
        return urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))

    async def health_check(self, endpoint: str) -> bool:
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(endpoint, timeout=5, allow_redirects=True) as resp:
                    return resp.status < 400
        except Exception:
            return False

    def extract_metadata(self, endpoint: str) -> str:
        import json
        return json.dumps({})

    def recheck_policy(self, status: str) -> float:
        if status == 'ACTIVE':
            return 30 * 24 * 3600
        elif status == 'STALE':
            return 3 * 24 * 3600
        return 24 * 3600

    async def crawl_jobs(self, endpoint: str, session: Any = None) -> Any:
        import re
        import time
        from src.jobs.models import CrawlResult
        
        # Determine board token
        match = re.search(r'greenhouse\.io/([^/]+)', endpoint)
        if not match:
            return CrawlResult(jobs=[], duration=0.0, api_calls=0, pages=0, errors=1, warnings=0, metadata={})
            
        board_token = match.group(1)
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
        
        start_time = time.time()
        jobs = []
        api_calls = 0
        errors = 0
        
        try:
            if session:
                async with session.get(api_url, timeout=10) as resp:
                    api_calls += 1
                    if resp.status == 200:
                        data = await resp.json()
                        jobs = data.get('jobs', [])
                    else:
                        errors += 1
        except Exception:
            errors += 1
            
        return CrawlResult(
            jobs=jobs,
            duration=time.time() - start_time,
            api_calls=api_calls,
            pages=1,
            errors=errors,
            warnings=0,
            metadata={"total": len(jobs)}
        )

    def normalize_job(self, raw_job: Any, company_id: str, endpoint: str = "") -> 'Job':
        from src.jobs.models import Job
        import hashlib
        
        title = raw_job.get('title', 'Unknown Title')
        department = "" # Requires greenhouse departments endpoint or detailed job
        location = raw_job.get('location', {}).get('name', 'Remote')
        description = "" 
        
        hash_input = f"{title}|{department}|{location}|{description}"
        job_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        external_id = str(raw_job.get('id', ''))
        
        return Job(
            job_id=f"greenhouse_{company_id}_{external_id}",
            company_id=company_id,
            ats_type='greenhouse',
            external_id=external_id,
            title=title,
            department=department,
            location=location,
            employment_type='',
            workplace_type='',
            posted_date=raw_job.get('updated_at', ''),
            updated_date='',
            apply_url=raw_job.get('absolute_url', ''),
            description=description,
            salary='',
            currency='',
            experience_level='',
            metadata=raw_job,
            job_hash=job_hash
        )
