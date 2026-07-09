from typing import List, Optional, Tuple, Any
from src.discovery.pipeline.fallback_models import DiscoveryPlugin
from src.discovery.models import BoardIdentity
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.inspectors.lever_inspector import LeverInspector
from src.discovery.pipeline.parsers import LeverParser

class LeverDiscoveryPlugin(DiscoveryPlugin):
    def __init__(self):
        self.parser = LeverParser()

    @property
    def provider_name(self) -> str:
        return "lever"
        
    def candidate_domains(self) -> List[str]:
        return ["jobs.lever.co"]
        
    def fingerprints(self) -> List[str]:
        return [
            "lever.co"
        ]
        
    def parse_candidate(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        return self.parser.parse(url)
        
    def inspector(self) -> SourceInspector:
        return LeverInspector()
        
    def confidence(self, evidence: Any) -> float:
        return 1.0

    def canonicalize(self, endpoint: str) -> str:
        import re
        canon = endpoint.split('?')[0].strip('/')
        # Remove trailing /jobs
        canon = re.sub(r'/jobs$', '', canon, flags=re.IGNORECASE)
        return canon

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
        
        match = re.search(r'jobs\.lever\.co/([^/]+)', endpoint)
        if not match:
            return CrawlResult(jobs=[], duration=0.0, api_calls=0, pages=0, errors=1, warnings=0, metadata={})
            
        board_token = match.group(1)
        api_url = f"https://api.lever.co/v0/postings/{board_token}"
        
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
                        # Lever API returns a list directly
                        if isinstance(data, list):
                            jobs = data
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
        
        title = raw_job.get('text', 'Unknown Title')
        
        categories = raw_job.get('categories', {})
        department = categories.get('team', '') 
        location = categories.get('location', 'Remote')
        workplace_type = categories.get('workplaceType', '')
        commitment = categories.get('commitment', '')
        
        description = raw_job.get('descriptionPlain', '')[:1000] # Usually detailed
        
        hash_input = f"{title}|{department}|{location}|{description}"
        job_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        external_id = str(raw_job.get('id', ''))
        
        return Job(
            job_id=f"lever_{company_id}_{external_id}",
            company_id=company_id,
            ats_type='lever',
            external_id=external_id,
            title=title,
            department=department,
            location=location,
            employment_type=commitment,
            workplace_type=workplace_type,
            posted_date=str(raw_job.get('createdAt', '')),
            updated_date='',
            apply_url=raw_job.get('hostedUrl', ''),
            description=description,
            salary='',
            currency='',
            experience_level='',
            metadata=raw_job,
            job_hash=job_hash
        )
