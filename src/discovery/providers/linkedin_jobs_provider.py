import yaml
import urllib.parse
from typing import List, Optional
from datetime import datetime
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.integrations.apify_manager import ApifyManager
from src.config.config import Config

class LinkedInJobsProvider(BaseProvider):
    def __init__(self):
        self._pipeline_type = 'PIPELINE_B'
        super().__init__()
        self.manager = ApifyManager()
        self.actor_id = Config.APIFY_ACTOR_ID or "hKByXkMQaC5Qt9UMN"
        
    def _get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            requires_api_key=True,
            supports_search_filters=True
        )
        
    def _load_preferences(self) -> dict:
        try:
            with open("src/config/user_preferences.yaml", "r") as f:
                return yaml.safe_load(f)
        except Exception:
            # Fallback preferences
            return {
                "target_roles": ["Product Manager", "Software Engineer"],
                "locations": ["India"]
            }

    def _generate_urls(self, prefs: dict) -> List[str]:
        roles = prefs.get("target_roles", ["Software Engineer"])
        locations = prefs.get("locations", ["India"])
        urls = []
        for role in roles:
            for loc in locations:
                query = urllib.parse.quote(role)
                location = urllib.parse.quote(loc)
                url = f"https://www.linkedin.com/jobs/search/?keywords={query}&location={location}"
                urls.append(url)
        return urls

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        prefs = self._load_preferences()
        urls = self._generate_urls(prefs)
        
        client, key_id = self.manager.get_client(tier=4, category="linkedin_pipeline_b")
        if not client:
            raise Exception("No Apify client available for LinkedIn jobs")
            
        print(f"LinkedInJobsProvider (Pipeline B): Searching {len(urls)} target combinations...")
        
        run_input = {
            "urls": urls,
            "maxItems": 10 # Hardcoded limit for now to prevent burning credits during dev
        }
        
        run = client.actor(self.actor_id).call(run_input=run_input)
        dataset_id = getattr(run, "default_dataset_id", getattr(run, "defaultDatasetId", None))
        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
            
        if not dataset_id:
            self.manager.record_usage(key_id, "linkedin_pipeline_b", credits=0, useful_results=0, success=False)
            raise Exception("Apify Run did not return a dataset ID")
            
        jobs = []
        for item in client.dataset(dataset_id).iterate_items():
            title = item.get("title", "Unknown")
            company = item.get("companyName", "Unknown")
            url = item.get("link", "")
            
            # Simple exclusion filter
            exclude_keywords = prefs.get("exclude_keywords", ["senior", "lead", "director", "manager"])
            title_lower = title.lower()
            if any(exc.lower() in title_lower for exc in exclude_keywords if exc.strip()):
                continue
                
            jobs.append(StandardJob(
                company=company,
                role=title,
                location=item.get("location", "Unknown"),
                remote_hybrid_onsite="Unknown",
                experience_required=item.get("seniorityLevel", ""),
                skills=[],
                job_description=item.get("descriptionText", ""),
                ats_type="linkedin",
                application_url=url,
                source="linkedin_jobs",
                date_posted=item.get("postedAt", datetime.now().isoformat())
            ))
            
        self.manager.record_usage(key_id, "linkedin_pipeline_b", credits=0.05, useful_results=len(jobs), success=True)
        return jobs
