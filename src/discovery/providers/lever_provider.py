import requests
from typing import List, Optional
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.crm.database import get_connection

class LeverProvider(BaseProvider):
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
        c.execute("SELECT lever_slug FROM company_intelligence_static WHERE lever_slug IS NOT NULL")
        slugs = [row[0] for row in c.fetchall()]
        conn.close()
        
        jobs_list = []
        for slug in slugs:
            try:
                url = f"https://api.lever.co/v0/postings/{slug}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for j in data:
                        # Lever uses createdAt
                        created_at = str(j.get("createdAt", ""))
                        if last_sync_timestamp and created_at and created_at < last_sync_timestamp:
                            continue
                            
                        location = j.get("categories", {}).get("location", "")
                        jobs_list.append(StandardJob(
                            company=slug.title(),
                            role=j.get("text", ""),
                            location=location,
                            remote_hybrid_onsite="Remote" if "remote" in location.lower() else "Unknown",
                            experience_required="Unknown",
                            skills=[],
                            job_description="",
                            ats_type="lever",
                            application_url=j.get("hostedUrl", ""),
                            source="lever_provider",
                            date_posted=created_at
                        ))
            except Exception:
                pass
                
        return jobs_list
