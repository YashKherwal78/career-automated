import requests
import time
import logging
import json
from typing import List, Dict, Any
from src.discovery.registry.company_orchestrator import CompanySource

logger = logging.getLogger("company_orchestrator")

def exponential_backoff(max_retries=3, backoff_factor=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        raise e
                    sleep_time = backoff_factor ** retries
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after {sleep_time}s due to {e}")
                    time.sleep(sleep_time)
        return wrapper
    return decorator

class YCAPIConnector(CompanySource):
    priority = 100
    name = "YCAPIConnector"
    
    def __init__(self, config: dict):
        pass

    @exponential_backoff(max_retries=1)
    def fetch_companies(self) -> List[Dict[str, Any]]:
        raise Exception("Deprecated. Relying on Algolia")

class OfficialYCConnector(CompanySource):
    priority = 80
    name = "OfficialYCConnector"
    
    def __init__(self, config: dict):
        pass

    @exponential_backoff(max_retries=3)
    def fetch_companies(self) -> List[Dict[str, Any]]:
        logger.info("[OfficialYCConnector] Hitting YC Algolia endpoint via facets...")
        headers = {
            "X-Algolia-Application-Id": "45BWZJ1SGC",
            "X-Algolia-API-Key": "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4ZTU0ZDlhYTZjOTJiMjlhMWFuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"
        }
        url = "https://45BWZJ1SGC-dsn.algolia.net/1/indexes/YCCompany_production/query"
        
        # Step 1: Get all batch facets
        payload = {"query": "", "facets": ["batch"], "maxValuesPerFacet": 500, "hitsPerPage": 0}
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        batches = list(resp.json().get("facets", {}).get("batch", {}).keys())
        
        all_companies = []
        for batch in batches:
            page = 0
            while True:
                payload = {
                    "query": "", 
                    "hitsPerPage": 1000, 
                    "page": page,
                    "facetFilters": [[f"batch:{batch}"]]
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=10)
                data = resp.json()
                hits = data.get("hits", [])
                if not hits: break
                
                for comp in hits:
                    all_companies.append({
                        "name": comp.get("name", ""),
                        "website": comp.get("website", ""),
                        "batch": comp.get("batch", ""),
                        "description": comp.get("long_description", comp.get("one_liner", "")),
                        "industry": comp.get("industry", ""),
                        "tags": comp.get("tags", []),
                        "location": comp.get("all_locations", ""),
                        "status": comp.get("status", "")
                    })
                page += 1
                if page >= data.get("nbPages", 1): break
        
        logger.info(f"[OfficialYCConnector] Successfully fully extracted {len(all_companies)} companies.")
        return all_companies

class OfficialAccelConnector(CompanySource):
    priority = 80
    name = "OfficialAccelConnector"
    
    def __init__(self, config: dict):
        pass

    @exponential_backoff(max_retries=3)
    def fetch_companies(self) -> List[Dict[str, Any]]:
        logger.info("[OfficialAccelConnector] Hitting Accel Sanity endpoint...")
        url = "https://458oembh.api.sanity.io/v1/data/query/production"
        query = '*[_type == "company"]{name, website}'
        resp = requests.get(url, params={"query": query}, timeout=10)
        data = resp.json()
        comps = []
        for c in data.get("result", []):
            comps.append({
                "name": c.get("name", ""),
                "website": c.get("website", "")
            })
        logger.info(f"[OfficialAccelConnector] Extracted {len(comps)} companies.")
        return comps

class OfficialPeakXVConnector(CompanySource):
    priority = 80
    name = "OfficialPeakXVConnector"
    def __init__(self, config: dict): pass
    def fetch_companies(self): return []

class GitHubConnector(CompanySource):
    priority = 20
    name = "GitHubConnector"
    def __init__(self, config: dict): pass
    def fetch_companies(self): return []

