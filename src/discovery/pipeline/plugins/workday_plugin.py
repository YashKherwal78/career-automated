from typing import List, Optional, Tuple, Any
from src.discovery.pipeline.fallback_models import DiscoveryPlugin
from src.discovery.models import BoardIdentity
from src.discovery.inspectors.base_inspector import SourceInspector
from src.discovery.inspectors.workday_inspector import WorkdayInspector
from src.discovery.pipeline.parsers import WorkdayParser

class WorkdayDiscoveryPlugin(DiscoveryPlugin):
    def __init__(self):
        self.parser = WorkdayParser()

    @property
    def provider_name(self) -> str:
        return "workday"
        
    def candidate_domains(self) -> List[str]:
        return ["myworkdayjobs.com", "apply.workday.com"]
        
    def fingerprints(self) -> List[str]:
        return [
            "myworkdayjobs",
            "wd1", "wd3", "wd5",
            "ExternalCareerSite",
            "wday/cxs",
            "apply.workday.com"
        ]
        
    def parse_candidate(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        return self.parser.parse(url)
        
    def inspector(self) -> SourceInspector:
        return WorkdayInspector()
        
    def confidence(self, evidence: Any) -> float:
        return 1.0

    def canonicalize(self, endpoint: str) -> str:
        # e.g., https://adobe.wd5.myworkdayjobs.com/en-US/External -> https://adobe.wd5.myworkdayjobs.com/
        import re
        canon = endpoint.split('?')[0].strip('/')
        # Remove trailing /en-US or /External
        canon = re.sub(r'/[a-zA-Z]{2}-[a-zA-Z]{2}/External$', '', canon, flags=re.IGNORECASE)
        canon = re.sub(r'/[a-zA-Z]{2}-[a-zA-Z]{2}$', '', canon, flags=re.IGNORECASE)
        canon = re.sub(r'/External$', '', canon, flags=re.IGNORECASE)
        if not canon.endswith('/'):
            canon += '/'
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
        import re
        # Example: https://adobe.wd5.myworkdayjobs.com/
        match = re.search(r'//([^.]+)\.([^.]+)\.', endpoint)
        if match:
            return json.dumps({
                "tenant": match.group(1),
                "cluster": match.group(2)
            })
        return "{}"

    def recheck_policy(self, status: str) -> float:
        if status == 'ACTIVE':
            return 30 * 24 * 3600
        elif status == 'STALE':
            return 3 * 24 * 3600
        return 24 * 3600

    async def crawl_jobs(self, endpoint: str, session: Any = None) -> Any:
        import re
        from src.jobs.models import CrawlResult
        import time

        match = re.search(r'//([^.]+)\.([^.]+)\.([^/]+)/([^/]+)', endpoint)
        if not match:
            return CrawlResult(jobs=[], duration=0.0, api_calls=0, pages=0, errors=1, warnings=0, metadata={})
            
        tenant = match.group(1)
        cluster = match.group(2)
        # myworkdayjobs.com is group 3
        board_id = match.group(4)
        
        api_url = f"https://{tenant}.{cluster}.myworkdayjobs.com/wday/cxs/{tenant}/{board_id}/jobs"
        
        payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        start_time = time.time()
        jobs = []
        api_calls = 0
        pages = 0
        errors = 0
        
        try:
            # We assume session is an aiohttp.ClientSession passed from the orchestrator
            if session:
                async with session.post(api_url, json=payload, headers=headers, timeout=10) as resp:
                    api_calls += 1
                    if resp.status == 200:
                        data = await resp.json()
                        jobs = data.get('jobPostings', [])
                        pages = 1
                    else:
                        errors += 1
        except Exception:
            errors += 1
            
        return CrawlResult(
            jobs=jobs,
            duration=time.time() - start_time,
            api_calls=api_calls,
            pages=pages,
            errors=errors,
            warnings=0,
            metadata={"total": len(jobs)}
        )

    def normalize_job(self, raw_job: Any, company_id: str, endpoint: str = "") -> 'Job':
        from src.jobs.models import Job
        import hashlib
        import re
        
        title = raw_job.get('title', 'Unknown Title')
        department = raw_job.get('jobFamilyGroup', '') # Often in bulletFields or jobFamilyGroup
        location = raw_job.get('locationsText', 'Remote')
        description = "" 
        
        # Build hash
        hash_input = f"{title}|{department}|{location}|{description}"
        job_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
        
        # Build apply_url
        apply_url = ""
        external_path = raw_job.get('externalPath', '')
        if endpoint:
            # e.g. https://adobe.wd5.myworkdayjobs.com/external_experienced -> https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/...
            match = re.search(r'(https://[^.]+\.[^.]+\.[^/]+)/([^/]+)', endpoint)
            if match:
                base = match.group(1)
                board = match.group(2)
                apply_url = f"{base}/en-US/{board}{external_path}"
        
        return Job(
            job_id=f"workday_{company_id}_{external_path.split('_')[-1] if '_' in external_path else external_path}",
            company_id=company_id,
            ats_type='workday',
            external_id=external_path,
            title=title,
            department=department,
            location=location,
            employment_type=raw_job.get('timeType', ''),
            workplace_type='',
            posted_date=raw_job.get('postedOn', ''),
            updated_date='',
            apply_url=apply_url,
            description=description,
            salary='',
            currency='',
            experience_level='',
            metadata=raw_job,
            job_hash=job_hash
        )
