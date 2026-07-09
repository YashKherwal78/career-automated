from src.system.logger import setup_logger
logger = setup_logger('google_jobs_provider')
import yaml
from typing import List, Optional
from datetime import datetime
from src.discovery.providers.base_provider import BaseProvider, StandardJob, ProviderCapabilities
from src.integrations.apify_manager import ApifyManager

class GoogleJobsProvider(BaseProvider):
    def __init__(self):
        self._pipeline_type = 'PIPELINE_B'
        super().__init__()
        self.manager = ApifyManager()
        self.actor_id = "hynekcasia/google-jobs-scraper"
        
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
            return {
                "target_roles": ["Product Manager", "Software Engineer"],
                "locations": ["India"]
            }

    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        prefs = self._load_preferences()
        roles = prefs.get("target_roles", ["Software Engineer"])
        locations = prefs.get("locations", ["India"])
        
        queries = []
        for role in roles:
            for loc in locations:
                queries.append(f"{role} jobs in {loc}")
                
        client, key_id = self.manager.get_client(tier=4, category="google_jobs_pipeline_b")
        if not client:
            raise Exception("No Apify client available for Google jobs")
            
        logger.info(f"GoogleJobsProvider (Pipeline B): Searching {len(queries)} queries...")
        
        run_input = {
            "queries": "\n".join(queries),
            "maxConcurrency": 5,
            "maxPagesPerQuery": 1
        }
        
        run = client.actor(self.actor_id).call(run_input=run_input)
        dataset_id = getattr(run, "default_dataset_id", getattr(run, "defaultDatasetId", None))
        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
            
        if not dataset_id:
            self.manager.record_usage(key_id, "google_jobs_pipeline_b", credits=0, useful_results=0, success=False)
            raise Exception("Apify Run did not return a dataset ID")
            
        jobs = []
        for item in client.dataset(dataset_id).iterate_items():
            title = item.get("title", "Unknown")
            company = item.get("companyName", "Unknown")
            url = item.get("applyLink", item.get("googleJobsUrl", ""))
            
            exclude_keywords = prefs.get("exclude_keywords", ["senior", "lead", "director", "manager"])
            if any(exc.lower() in title.lower() for exc in exclude_keywords if exc.strip()):
                continue
                
            jobs.append(StandardJob(
                company=company,
                role=title,
                location=item.get("location", "Unknown"),
                remote_hybrid_onsite="Unknown",
                experience_required="",
                skills=[],
                job_description=item.get("description", ""),
                ats_type="google_jobs",
                application_url=url,
                source="google_jobs",
                date_posted=item.get("postedAt", datetime.now().isoformat())
            ))
            
        self.manager.record_usage(key_id, "google_jobs_pipeline_b", credits=0.05, useful_results=len(jobs), success=True)
        return jobs
