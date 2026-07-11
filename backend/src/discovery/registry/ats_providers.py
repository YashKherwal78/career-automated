import re
import json
import hashlib
import time
from typing import Protocol, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

@dataclass
class EndpointIdentity:
    provider: str
    identifiers: dict[str, str] = field(default_factory=dict)

@dataclass
class ProviderCapabilities:
    supports_jobs: bool = True
    supports_incremental: bool = False
    supports_health_checks: bool = True

@dataclass
class VerificationResult:
    endpoint_id: str
    company_id: str
    company_name: str
    provider: str
    endpoint: str
    canonical_endpoint: str
    endpoint_identity: EndpointIdentity
    healthy: bool
    verified: bool
    confidence: float
    inspector_score: float
    identity_score: float
    reason: Optional[str]
    metadata: dict
    plugin_name: str
    plugin_version: str
    provider_version: str
    verification_version: str = "v2"
    latency_ms: int = 0
    attempt_number: int = 1
    next_retry_after: Optional[float] = None

class ATSProvider(Protocol):
    name: str
    plugin_version: str
    provider_version: str
    
    def capabilities(self) -> ProviderCapabilities: ...
    def parse_endpoint(self, url: str) -> EndpointIdentity: ...
    async def health_check(self, session: aiohttp.ClientSession, identity: EndpointIdentity, url: str) -> bool: ...
    async def inspect(self, session: aiohttp.ClientSession, identity: EndpointIdentity) -> Tuple[bool, dict]: ...
    def identity_validate(self, target_company: str, metadata: dict) -> Tuple[bool, float]: ...
    async def verify(self, session: aiohttp.ClientSession, url: str, company_name: str, endpoint_id: str, company_id: str) -> VerificationResult: ...
    
    # Backwards compatibility methods
    def generate_candidate_urls(self, slug: str) -> List[str]: ...
    def verify_compat(self, response_data: dict) -> bool: ...
    def extract_metadata(self, response_data: dict) -> dict: ...
    async def fetch_jobs(self, session: aiohttp.ClientSession, slug: str) -> List[dict]: ...
    def normalize_job(self, company_id: str, raw_job: dict) -> dict: ...
    def compute_hash(self, normalized_job: dict) -> str: ...
    async def probe(self, session: aiohttp.ClientSession, slug: str) -> Tuple[bool, dict, str]: ...

def hash_job(title: str, location: str, desc: str) -> str:
    content = f"{title}|{location}|{desc}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()

class BaseATSProvider:
    name: str = "Base"
    plugin_version: str = "1.0"
    provider_version: str = "base-v1"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    def parse_endpoint(self, url: str) -> EndpointIdentity:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        slug = path.split('/')[-1] if path else ""
        return EndpointIdentity(provider=self.name, identifiers={"slug": slug})

    async def health_check(self, session: aiohttp.ClientSession, identity: EndpointIdentity, url: str) -> bool:
        try:
            async with session.head(url, timeout=5, allow_redirects=True) as resp:
                return resp.status < 400
        except Exception:
            return False

    async def inspect(self, session: aiohttp.ClientSession, identity: EndpointIdentity) -> Tuple[bool, dict]:
        # Subclasses should implement actual inspection and return (success, metadata)
        return True, {}

    def identity_validate(self, target_company: str, metadata: dict) -> Tuple[bool, float]:
        # Subclasses should implement company identity validation and return (is_valid, confidence_score)
        return True, 0.5

    async def verify(self, session: aiohttp.ClientSession, url: str, company_name: str, endpoint_id: str, company_id: str) -> VerificationResult:
        start_time = time.time()
        try:
            identity = self.parse_endpoint(url)
            
            # 1. Health Check
            is_healthy = await self.health_check(session, identity, url)
            if not is_healthy:
                latency = int((time.time() - start_time) * 1000)
                return VerificationResult(
                    endpoint_id=endpoint_id,
                    company_id=company_id,
                    company_name=company_name,
                    provider=self.name,
                    endpoint=url,
                    canonical_endpoint=url,
                    endpoint_identity=identity,
                    healthy=False,
                    verified=False,
                    confidence=0.0,
                    inspector_score=0.0,
                    identity_score=0.0,
                    reason="Health check failed: endpoint is unreachable",
                    metadata={},
                    plugin_name=self.__class__.__name__,
                    plugin_version=self.plugin_version,
                    provider_version=self.provider_version,
                    latency_ms=latency
                )

            # 2. Inspect (Probe metadata)
            inspect_ok, metadata = await self.inspect(session, identity)
            if not inspect_ok:
                latency = int((time.time() - start_time) * 1000)
                return VerificationResult(
                    endpoint_id=endpoint_id,
                    company_id=company_id,
                    company_name=company_name,
                    provider=self.name,
                    endpoint=url,
                    canonical_endpoint=url,
                    endpoint_identity=identity,
                    healthy=True,
                    verified=False,
                    confidence=0.0,
                    inspector_score=0.0,
                    identity_score=0.0,
                    reason="Inspection failed: invalid board or ATS response",
                    metadata={},
                    plugin_name=self.__class__.__name__,
                    plugin_version=self.plugin_version,
                    provider_version=self.provider_version,
                    latency_ms=latency
                )

            # 3. Identity Validation
            identity_ok, identity_score = self.identity_validate(company_name, metadata)
            if not identity_ok:
                latency = int((time.time() - start_time) * 1000)
                return VerificationResult(
                    endpoint_id=endpoint_id,
                    company_id=company_id,
                    company_name=company_name,
                    provider=self.name,
                    endpoint=url,
                    canonical_endpoint=url,
                    endpoint_identity=identity,
                    healthy=True,
                    verified=False,
                    confidence=0.0,
                    inspector_score=1.0,
                    identity_score=identity_score,
                    reason=f"Identity mismatch against '{company_name}'",
                    metadata=metadata,
                    plugin_name=self.__class__.__name__,
                    plugin_version=self.plugin_version,
                    provider_version=self.provider_version,
                    latency_ms=latency
                )

            # 4. Final promotion mapping
            final_confidence = 0.5 * 1.0 + 0.5 * identity_score
            latency = int((time.time() - start_time) * 1000)
            return VerificationResult(
                endpoint_id=endpoint_id,
                company_id=company_id,
                company_name=company_name,
                provider=self.name,
                endpoint=url,
                canonical_endpoint=url,
                endpoint_identity=identity,
                healthy=True,
                verified=True,
                confidence=final_confidence,
                inspector_score=1.0,
                identity_score=identity_score,
                reason=None,
                metadata=metadata,
                plugin_name=self.__class__.__name__,
                plugin_version=self.plugin_version,
                provider_version=self.provider_version,
                latency_ms=latency
            )

        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            return VerificationResult(
                endpoint_id=endpoint_id,
                company_id=company_id,
                company_name=company_name,
                provider=self.name,
                endpoint=url,
                canonical_endpoint=url,
                endpoint_identity=EndpointIdentity(provider=self.name, identifiers={}),
                healthy=False,
                verified=False,
                confidence=0.0,
                inspector_score=0.0,
                identity_score=0.0,
                reason=str(e),
                metadata={},
                plugin_name=self.__class__.__name__,
                plugin_version=self.plugin_version,
                provider_version=self.provider_version,
                latency_ms=latency
            )

class GreenhouseProvider(BaseATSProvider):
    name = "Greenhouse"
    plugin_version = "1.0"
    provider_version = "greenhouse-v1"

    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify_compat(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}

    def parse_endpoint(self, url: str) -> EndpointIdentity:
        url_clean = url.split('?')[0].strip().rstrip('/')
        match = re.search(r'boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([^/]+)', url_clean)
        slug = match.group(1) if match else url_clean.split('/')[-1]
        return EndpointIdentity(provider=self.name, identifiers={"slug": slug})

    async def health_check(self, session: aiohttp.ClientSession, identity: EndpointIdentity, url: str) -> bool:
        check_url = f"https://boards-api.greenhouse.io/v1/boards/{identity.identifiers.get('slug')}/jobs"
        try:
            async with session.head(check_url, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def inspect(self, session: aiohttp.ClientSession, identity: EndpointIdentity) -> Tuple[bool, dict]:
        is_healthy, metadata, _ = await self.probe(session, identity.identifiers.get('slug'))
        return is_healthy, metadata

    def identity_validate(self, target_company: str, metadata: dict) -> Tuple[bool, float]:
        canon_name = metadata.get("company_name", "")
        if not target_company or not canon_name:
            return True, 0.5
        target_norm = re.sub(r'[^a-z0-9]', '', re.sub(r'\b(inc|llc|ltd|corp|corporation|company)\b\.?', '', target_company.lower()))
        canon_norm = re.sub(r'[^a-z0-9]', '', re.sub(r'\b(inc|llc|ltd|corp|corporation|company)\b\.?', '', canon_name.lower()))
        if target_norm in canon_norm or canon_norm in target_norm:
            return True, 1.0
        return False, 0.0
    
    async def probe(self, session, slug):
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if 'jobs' in data: return True, {"company_name": data.get("name", ""), "job_count": len(data.get("jobs", []))}, url
        except Exception: pass
        return False, {}, ""
        
    async def fetch_jobs(self, session, slug):
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('jobs', [])
        except Exception: pass
        return []
        
    def normalize_job(self, company_id, raw_job):
        title = raw_job.get("title", "")
        location = raw_job.get("location", {}).get("name", "Remote")
        desc = raw_job.get("content", "")
        clean_desc = BeautifulSoup(desc, "html.parser").get_text() if desc else ""
        j_hash = hash_job(title, location, clean_desc)
        return {
            "job_id": f"gh_{raw_job.get('id')}",
            "provider_job_id": str(raw_job.get("id")),
            "company_id": company_id,
            "provider": self.name,
            "title": title,
            "location": location,
            "apply_url": raw_job.get("absolute_url"),
            "description": clean_desc,
            "job_hash": j_hash,
            "raw_payload_json": json.dumps(raw_job)
        }
    def compute_hash(self, nj): return nj["job_hash"]

class LeverProvider(BaseATSProvider):
    name = "Lever"
    plugin_version = "1.0"
    provider_version = "lever-v1"

    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify_compat(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}

    def parse_endpoint(self, url: str) -> EndpointIdentity:
        url_clean = url.split('?')[0].strip().rstrip('/')
        match = re.search(r'(?:jobs|api)\.lever\.co/(?:v0/postings/)?([^/]+)', url_clean)
        slug = match.group(1) if match else url_clean.split('/')[-1]
        return EndpointIdentity(provider=self.name, identifiers={"slug": slug})

    async def health_check(self, session: aiohttp.ClientSession, identity: EndpointIdentity, url: str) -> bool:
        check_url = f"https://api.lever.co/v0/postings/{identity.identifiers.get('slug')}"
        try:
            async with session.head(check_url, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def inspect(self, session: aiohttp.ClientSession, identity: EndpointIdentity) -> Tuple[bool, dict]:
        is_healthy, metadata, _ = await self.probe(session, identity.identifiers.get('slug'))
        return is_healthy, metadata

    def identity_validate(self, target_company: str, metadata: dict) -> Tuple[bool, float]:
        # Lever API postings endpoint does not return company name, so we validate neutrally based on slug match
        return True, 0.8

    async def probe(self, session, slug):
        url = f"https://api.lever.co/v0/postings/{slug}"
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list): return True, {"company_name": "", "job_count": len(data)}, url
        except Exception: pass
        return False, {}, ""
        
    async def fetch_jobs(self, session, slug):
        url = f"https://api.lever.co/v0/postings/{slug}"
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200: return await resp.json()
        except Exception: pass
        return []
        
    def normalize_job(self, company_id, raw_job):
        title = raw_job.get("text", "")
        location = raw_job.get("categories", {}).get("location", "Remote")
        team = raw_job.get("categories", {}).get("team", "")
        desc = raw_job.get("descriptionPlain", "")
        j_hash = hash_job(title, location, desc)
        return {
            "job_id": f"lv_{raw_job.get('id')}",
            "provider_job_id": raw_job.get("id"),
            "company_id": company_id,
            "provider": self.name,
            "title": title,
            "location": location,
            "team": team,
            "apply_url": raw_job.get("hostedUrl"),
            "description": desc,
            "job_hash": j_hash,
            "raw_payload_json": json.dumps(raw_job)
        }
    def compute_hash(self, nj): return nj["job_hash"]

class AshbyProvider(BaseATSProvider):
    name = "Ashby"
    plugin_version = "1.0"
    provider_version = "ashby-v1"

    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify_compat(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}

    def parse_endpoint(self, url: str) -> EndpointIdentity:
        url_clean = url.split('?')[0].strip().rstrip('/')
        match = re.search(r'api\.ashbyhq\.com/posting-api/job-board/([^/]+)', url_clean)
        slug = match.group(1) if match else url_clean.split('/')[-1]
        return EndpointIdentity(provider=self.name, identifiers={"slug": slug})

    async def health_check(self, session: aiohttp.ClientSession, identity: EndpointIdentity, url: str) -> bool:
        check_url = f"https://api.ashbyhq.com/posting-api/job-board/{identity.identifiers.get('slug')}"
        try:
            async with session.head(check_url, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def inspect(self, session: aiohttp.ClientSession, identity: EndpointIdentity) -> Tuple[bool, dict]:
        is_healthy, metadata, _ = await self.probe(session, identity.identifiers.get('slug'))
        return is_healthy, metadata

    def identity_validate(self, target_company: str, metadata: dict) -> Tuple[bool, float]:
        # Ashby doesn't return canonical company name in job-board API, validate neutrally
        return True, 0.8

    async def probe(self, session, slug):
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "jobs" in data: return True, {"company_name": "", "job_count": len(data.get("jobs", []))}, url
        except Exception: pass
        return False, {}, ""
        
    async def fetch_jobs(self, session, slug):
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        try:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('jobs', [])
        except Exception: pass
        return []
        
    def normalize_job(self, company_id, raw_job):
        title = raw_job.get("title", "")
        location = raw_job.get("location", "Remote")
        desc = raw_job.get("descriptionHtml", "")
        clean_desc = BeautifulSoup(desc, "html.parser").get_text() if desc else ""
        j_hash = hash_job(title, location, clean_desc)
        return {
            "job_id": f"as_{raw_job.get('id')}",
            "provider_job_id": str(raw_job.get("id")),
            "company_id": company_id,
            "provider": self.name,
            "title": title,
            "location": location,
            "department": raw_job.get("department"),
            "apply_url": raw_job.get("jobUrl"),
            "description": clean_desc,
            "job_hash": j_hash,
            "raw_payload_json": json.dumps(raw_job)
        }
    def compute_hash(self, nj): return nj["job_hash"]

class WorkableProvider(BaseATSProvider):
    name = "Workable"
    plugin_version = "1.0"
    provider_version = "workable-v1"

    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify_compat(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}

    def parse_endpoint(self, url: str) -> EndpointIdentity:
        url_clean = url.split('?')[0].strip().rstrip('/')
        match = re.search(r'apply\.workable\.com/(?:api/v3/accounts/)?([^/]+)', url_clean)
        slug = match.group(1) if match else url_clean.split('/')[-1]
        return EndpointIdentity(provider=self.name, identifiers={"slug": slug})

    async def health_check(self, session: aiohttp.ClientSession, identity: EndpointIdentity, url: str) -> bool:
        check_url = f"https://apply.workable.com/api/v3/accounts/{identity.identifiers.get('slug')}/jobs"
        try:
            async with session.post(check_url, json={"token":""}, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    async def inspect(self, session: aiohttp.ClientSession, identity: EndpointIdentity) -> Tuple[bool, dict]:
        is_healthy, metadata, _ = await self.probe(session, identity.identifiers.get('slug'))
        return is_healthy, metadata

    def identity_validate(self, target_company: str, metadata: dict) -> Tuple[bool, float]:
        return True, 0.8

    async def probe(self, session, slug):
        url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
        try:
            async with session.post(url, json={"token":""}, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if "results" in data: return True, {"company_name": "", "job_count": data.get("total", 0)}, url
        except Exception: pass
        return False, {}, ""
        
    async def fetch_jobs(self, session, slug):
        url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
        try:
            async with session.post(url, json={"token":""}, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("results", [])
        except Exception: pass
        return []
        
    def normalize_job(self, company_id, raw_job):
        title = raw_job.get("title", "")
        location = f"{raw_job.get('location', {}).get('city', '')} {raw_job.get('location', {}).get('country', '')}"
        j_hash = hash_job(title, location, "")
        return {
            "job_id": f"wk_{raw_job.get('shortcode')}",
            "provider_job_id": raw_job.get("shortcode"),
            "company_id": company_id,
            "provider": self.name,
            "title": title,
            "location": location.strip(),
            "department": raw_job.get("department", ""),
            "apply_url": f"https://apply.workable.com/j/{raw_job.get('shortcode')}",
            "description": "",
            "job_hash": j_hash,
            "raw_payload_json": json.dumps(raw_job)
        }
    def compute_hash(self, nj): return nj["job_hash"]

class DefaultStubProvider(BaseATSProvider):
    name = "Unknown"
    plugin_version = "1.0"
    provider_version = "stub-v1"

    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify_compat(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}
    async def probe(self, session, slug): return False, {}, ""
    async def fetch_jobs(self, session, slug): return []
    def normalize_job(self, company_id, raw_job): return {}
    def compute_hash(self, nj): return ""

class ProviderRegistry:
    providers = [
        GreenhouseProvider(), LeverProvider(), AshbyProvider(), WorkableProvider()
    ]
        
    @classmethod
    def get_providers(cls):
        return cls.providers
    
    @classmethod
    def get_provider_by_name(cls, name: str) -> Optional[ATSProvider]:
        for p in cls.providers:
            if p.name.lower() == name.lower(): return p
        return None

    @classmethod
    def resolve(cls, url: str) -> Optional[ATSProvider]:
        url_lower = url.lower()
        if "greenhouse.io" in url_lower:
            return GreenhouseProvider()
        if "lever.co" in url_lower:
            return LeverProvider()
        if "ashbyhq.com" in url_lower:
            return AshbyProvider()
        if "workable.com" in url_lower:
            return WorkableProvider()
        return None
