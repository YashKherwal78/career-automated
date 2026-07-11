from typing import Dict, Any, List, Tuple
from apify_client import ApifyClient
from src.discovery.connectors.search_connector_base import SearchConnectorBase
from src.discovery.discovery_connector import ConnectorCapabilityMatrix
from src.discovery.search_planner import SearchTask
from src.common.credential_provider import CredentialFactory, Credential

class IndeedConnector(SearchConnectorBase):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.actor_id = config.get("actor")
        self.credentials = CredentialFactory.get("APIFY")

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

    def health_check(self) -> bool:
        try:
            def fetch_health(credential: Credential):
                client = ApifyClient(credential.secret)
                actor = client.actor(self.actor_id).get()
                return actor is not None
            return self.credentials.execute_sync(fetch_health)
        except Exception:
            return False

    def execute_search(self, task: SearchTask) -> Tuple[List[Any], List[str]]:
        warnings = []
        
        max_age_days = task.freshness_days
        keyword_str = task.canonical_query
        
        if "Remote" in task.work_modes:
            keyword_str += " remote"
            
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
        
        def fetch_run(credential: Credential):
            client = ApifyClient(credential.secret)
            run = client.actor(self.actor_id).call(run_input=run_input)
            
            dataset_id = getattr(run, "default_dataset_id", None)
            if not dataset_id and isinstance(run, dict):
                dataset_id = run.get("defaultDatasetId")
                
            jobs = []
            if dataset_id:
                for item in client.dataset(dataset_id).iterate_items():
                    jobs.append(item)
            return jobs
            
        jobs = self.credentials.execute_sync(fetch_run)
                
        return jobs, warnings

    def metrics(self) -> Dict[str, Any]:
        return {"retrieval": "apify"}

    def shutdown(self) -> None:
        pass
