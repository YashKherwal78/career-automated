import os
from typing import Dict, Any, List, Tuple
from apify_client import ApifyClient
from src.discovery.connectors.search_connector_base import SearchConnectorBase
from src.discovery.discovery_connector import ConnectorCapabilityMatrix
from src.discovery.search_planner import SearchTask

class IndeedConnector(SearchConnectorBase):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.actor_id = config.get("actor")
        self.client = None

    @property
    def name(self) -> str:
        return "IndeedConnector"

    def get_capabilities(self) -> ConnectorCapabilityMatrix:
        return ConnectorCapabilityMatrix(
            objective="Market Discovery",
            target="opportunities",
            discover_jobs=True,
            discover_companies=True,
            confidence_score=75,
            supports_native_freshness=True,
            supports_native_sort=True,
            supports_max_items=True,
            supports_company_search=True,
            supports_semantic_search=True,
            supports_experience_filter=True,
            supports_remote_filter=True,
            supports_employment_filter=True,
            supports_location_filter=True
        )

    def initialize(self) -> None:
        if not self.actor_id:
            raise ValueError("Indeed actor ID not configured in connectors.yaml")
        api_key = os.getenv("APIFY_KEY_1") or os.getenv("APIFY_API_KEY")
        if not api_key:
            raise ValueError("APIFY_KEY_1 is missing.")
        self.client = ApifyClient(api_key)

    def health_check(self) -> bool:
        try:
            actor = self.client.actor(self.actor_id).get()
            return actor is not None
        except Exception:
            return False

    def execute_search(self, task: SearchTask) -> Tuple[List[Any], List[str]]:
        """
        Translates a business-level SearchTask into the platform-specific Indeed Apify query.
        """
        warnings = []
        
        # Map freshness_days to maxAgeDays (just pass it directly if integer)
        max_age_days = task.freshness_days
        
        keyword_str = task.canonical_query
        
        # Indeed Apify Actors (like hynekcasia/indeed-scraper) often support explvl and remote parameters in the query
        if "Remote" in task.work_modes:
            keyword_str += " remote"
            
        # Example mapping for Indeed (often they just use query additions if exact parameters aren't explicitly passed, 
        # or the scraper accepts explicit 'explvl' if documented)
        if "Entry" in task.experience_profile or "Associate" in task.experience_profile:
            keyword_str += " entry level"

        run_input = {
            "position": keyword_str,
            "location": task.locations[0],
            "sort": "date",
            "maxAgeDays": max_age_days,
            "maxItems": task.budget.get("max_results", 50),
            "maxConcurrency": 1
        }
        
        # Hard 90s timeout is enforced logic-side in Base
        run = self.client.actor(self.actor_id).call(run_input=run_input)
        
        dataset_id = getattr(run, "default_dataset_id", None)
        if not dataset_id and isinstance(run, dict):
            dataset_id = run.get("defaultDatasetId")
            
        jobs = []
        if dataset_id:
            for item in self.client.dataset(dataset_id).iterate_items():
                jobs.append(item)
                
        return jobs, warnings

    def metrics(self) -> Dict[str, Any]:
        return {"retrieval": "apify"}

    def shutdown(self) -> None:
        pass
