import re
import json
import hashlib
from typing import Protocol, List, Tuple, Optional
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

class ATSProvider(Protocol):
    name: str
    def generate_candidate_urls(self, slug: str) -> List[str]: ...
    def verify(self, response_data: dict) -> bool: ...
    def extract_metadata(self, response_data: dict) -> dict: ...
    async def fetch_jobs(self, session: aiohttp.ClientSession, slug: str) -> List[dict]: ...
    def normalize_job(self, company_id: str, raw_job: dict) -> dict: ...
    def compute_hash(self, normalized_job: dict) -> str: ...
    async def probe(self, session: aiohttp.ClientSession, slug: str) -> Tuple[bool, dict, str]: ...

def hash_job(title: str, location: str, desc: str) -> str:
    content = f"{title}|{location}|{desc}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()

class GreenhouseProvider:
    name = "Greenhouse"
    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}
    
    async def probe(self, session, slug):
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        try:
            async with session.get(url, timeout=3) as resp:
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

class LeverProvider:
    name = "Lever"
    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}
    async def probe(self, session, slug):
        url = f"https://api.lever.co/v0/postings/{slug}"
        try:
            async with session.get(url, timeout=3) as resp:
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

class AshbyProvider:
    name = "Ashby"
    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}
    async def probe(self, session, slug):
        url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
        try:
            async with session.get(url, timeout=3) as resp:
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

class WorkableProvider:
    name = "Workable"
    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}
    async def probe(self, session, slug):
        url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
        try:
            async with session.post(url, json={"token":""}, timeout=3) as resp:
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


# Default stub for remaining providers to satisfy the protocol interface for Sprint 1.6A Exit Criteria
class DefaultStubProvider:
    name = "Unknown"
    def generate_candidate_urls(self, slug: str) -> List[str]: return []
    def verify(self, response_data: dict) -> bool: return False
    def extract_metadata(self, response_data: dict) -> dict: return {}
    async def probe(self, session, slug): return False, {}, ""
    async def fetch_jobs(self, session, slug): return []
    def normalize_job(self, company_id, raw_job): return {}
    def compute_hash(self, nj): return ""

class ProviderRegistry:
    def __init__(self):
        self.providers = [
            GreenhouseProvider(), LeverProvider(), AshbyProvider(), WorkableProvider()
        ]
        
    def get_providers(self):
        return self.providers
    
    def get_provider_by_name(self, name: str) -> Optional[ATSProvider]:
        for p in self.providers:
            if p.name.lower() == name.lower(): return p
        return None
