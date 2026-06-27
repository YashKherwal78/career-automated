import requests
from typing import List, Optional
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.crm.database import get_connection

class AshbyProvider(BaseProvider):
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            requires_api_key=False,
            rate_limit_per_minute=60,
            supports_pagination=False,
            supports_incremental_sync=True,
            supports_remote_jobs=True,
            supports_search_filters=False
        )

    def validate_configuration(self) -> bool:
        return True

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT ashby_slug FROM company_intelligence_static WHERE ashby_slug IS NOT NULL")
        slugs = [row[0] for row in c.fetchall()]
        conn.close()
        
        jobs_list = []
        for slug in slugs:
            try:
                # Ashby provides a public jobs API endpoint
                url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for j in data.get("jobs", []):
                        published_at = j.get("publishedAt", "")
                        if last_sync_timestamp and published_at and published_at < last_sync_timestamp:
                            continue
                            
                        jobs_list.append(StandardJob(
                            company=slug.title(),
                            role=j.get("title", ""),
                            location=j.get("locationName", ""),
                            remote_hybrid_onsite="Remote" if j.get("isRemote") else "Unknown",
                            experience_required="Unknown",
                            skills=[],
                            job_description="",
                            ats_type="ashby",
                            application_url=j.get("jobUrl", ""),
                            source="ashby_provider",
                            date_posted=published_at
                        ))
            except Exception:
                pass
                
        return jobs_list
