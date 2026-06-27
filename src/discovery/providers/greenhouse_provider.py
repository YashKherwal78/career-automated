import requests
from typing import List, Optional
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.crm.database import get_connection

class GreenhouseProvider(BaseProvider):
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            requires_api_key=False,
            rate_limit_per_minute=60,
            supports_pagination=True,
            supports_incremental_sync=True,
            supports_remote_jobs=True,
            supports_search_filters=False
        )

    def validate_configuration(self) -> bool:
        # Greenhouse Boards API is public, no auth needed.
        return True

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT greenhouse_slug FROM company_intelligence_static WHERE greenhouse_slug IS NOT NULL")
        slugs = [row[0] for row in c.fetchall()]
        conn.close()
        
        jobs_list = []
        for slug in slugs:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for j in data.get("jobs", []):
                        # Filter by timestamp if provided
                        updated_at = j.get("updated_at", "")
                        if last_sync_timestamp and updated_at and updated_at < last_sync_timestamp:
                            continue
                            
                        jobs_list.append(StandardJob(
                            company=slug.title(),
                            role=j.get("title", ""),
                            location=j.get("location", {}).get("name", ""),
                            remote_hybrid_onsite="Remote" if "remote" in j.get("location", {}).get("name", "").lower() else "Unknown",
                            experience_required="Unknown",
                            skills=[],
                            job_description="",
                            ats_type="greenhouse",
                            application_url=j.get("absolute_url", ""),
                            source="greenhouse_provider",
                            date_posted=updated_at
                        ))
            except Exception:
                pass
                
        return jobs_list
