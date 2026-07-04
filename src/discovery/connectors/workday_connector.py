import requests
from typing import List, Dict, Optional
import json
import re
from datetime import datetime

from src.discovery.discovery_connector import DiscoveryConnector, ConnectorCapabilityMatrix

class WorkdayConnector(DiscoveryConnector):
    def __init__(self):
        super().__init__()
        self.capabilities = ConnectorCapabilityMatrix(
            objective="Official Discovery",
            target="opportunities",
            discover_jobs=True,
            produces_official_apply_urls=True,
            confidence_score=90
        )

    def verify_connection(self) -> bool:
        return True
        
    def initialize(self) -> bool:
        return True
        
    def get_capabilities(self) -> ConnectorCapabilityMatrix:
        return self.capabilities
        
    def health_check(self) -> Dict:
        return {"status": "healthy"}
        
    def metrics(self) -> Dict:
        return {"requests": 0}
        
    def shutdown(self):
        pass
        
    def discover(self, target: str, **kwargs) -> Dict:
        return self.discover_opportunities(target, **kwargs)

    def extract_tenant_info(self, url: str) -> tuple:
        """Extracts workday tenant and custom site from a base url."""
        # E.g. https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternal
        match = re.match(r'https://([^.]+)\.([^.]+)\.myworkdayjobs\.com/([^/]+)', url)
        if match:
            return match.group(1), match.group(2), match.group(3)
        return None, None, None

    def discover_opportunities(self, target: str, **kwargs) -> Dict:
        """
        Target should be the base url, e.g. https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternal
        """
        tenant, region, custom_site = self.extract_tenant_info(target)
        if not custom_site:
            return {
                "status": "DEGRADED",
                "opportunities": [],
                "metadata": {"error": "Invalid Workday base URL provided."}
            }
            
        api_endpoint = f"https://{tenant}.{region}.myworkdayjobs.com/wday/cxs/{tenant}/{custom_site}/jobs"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        payload = {
            "appliedFacets": {},
            "limit": 20,
            "offset": 0,
            "searchText": ""
        }
        
        try:
            resp = requests.post(api_endpoint, json=payload, headers=headers, timeout=10)
            if resp.status_code != 200:
                # Try fallback endpoint structure
                api_endpoint = f"https://{tenant}.{region}.myworkdayjobs.com/wday/cxs/{custom_site}/jobs"
                resp = requests.post(api_endpoint, json=payload, headers=headers, timeout=10)
                
            if resp.status_code != 200:
                return {
                    "status": "DEGRADED",
                    "opportunities": [],
                    "metadata": {"error": f"Unsupported Workday tenant API. Status: {resp.status_code}"}
                }
                
            data = resp.json()
            jobs = data.get("jobPostings", [])
            
            normalized_jobs = []
            for j in jobs:
                normalized_jobs.append({
                    "id": j.get("bulletinID") or j.get("id"),
                    "title": j.get("title", ""),
                    "companyName": tenant.capitalize(),
                    "location": j.get("locationsText", "Unknown"),
                    "link": f"https://{tenant}.{region}.myworkdayjobs.com/en-US/{custom_site}{j.get('externalPath', '')}",
                    "applyUrl": f"https://{tenant}.{region}.myworkdayjobs.com/en-US/{custom_site}{j.get('externalPath', '')}/apply",
                    "descriptionText": "Details available on Workday.",
                    "connector_override": "workday",
                    "source_platform_override": "Workday"
                })
                
            return {
                "status": "SUCCESS",
                "opportunities": normalized_jobs,
                "metadata": {
                    "workday_tenant": tenant,
                    "workday_region": region,
                    "workday_version": "v1"
                }
            }
            
        except Exception as e:
            return {
                "status": "DEGRADED",
                "opportunities": [],
                "metadata": {"error": str(e)}
            }
