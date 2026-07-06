import aiohttp
from typing import Dict, Any, List
from src.discovery.registry.source_adapter import SourceAdapter

class GreenhouseAdapter(SourceAdapter):
    
    @property
    def source_name(self) -> str:
        return "greenhouse"
        
    @property
    def parser_version(self) -> str:
        return "v2.0"
        
    def detect(self, url: str) -> bool:
        return "boards.greenhouse.io" in url or "boards-api.greenhouse.io" in url
        
    async def fetch(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Fetches the Greenhouse API payload for a specific board."""
        url = task.get("url", "")
        # Convert standard board URL to API URL if needed
        if "boards.greenhouse.io" in url and not "boards-api" in url:
            board_token = url.rstrip('/').split('/')[-1]
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
        else:
            api_url = url
            
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                response.raise_for_status()
                return await response.json()
                
    def parse(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """The Greenhouse payload is already structured JSON, just pass it through."""
        return raw_payload
        
    def discover_jobs(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = []
        for raw_job in parsed_data.get("jobs", []):
            job = {
                "title": raw_job.get("title"),
                "location": raw_job.get("location", {}).get("name"),
                "apply_url": raw_job.get("absolute_url"),
                "provider_job_id": str(raw_job.get("id")),
                "updated_at": raw_job.get("updated_at"),
                "provider": self.source_name
            }
            jobs.append(job)
        return jobs
        
    def discover_companies(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Greenhouse board API represents a single company, not aggregators
        return []

# Register the adapter automatically when module is imported
from src.discovery.registry.source_registry import SourceRegistry
SourceRegistry.register(GreenhouseAdapter)
