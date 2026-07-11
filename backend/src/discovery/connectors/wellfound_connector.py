from typing import Dict, Any, List, Tuple
from apify_client import ApifyClient
from src.discovery.connectors.search_connector_base import SearchConnectorBase
from src.discovery.discovery_connector import ConnectorCapabilityMatrix
from src.discovery.search_planner import SearchTask
from src.common.credential_provider import CredentialFactory, Credential

class WellfoundConnector(SearchConnectorBase):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.actor_id = config.get("actor", "clearpath/wellfound-api-ppe")
        self.credentials = CredentialFactory.get("APIFY")

    @property
    def name(self) -> str:
        return "WellfoundConnector"

    def get_capabilities(self) -> ConnectorCapabilityMatrix:
        return ConnectorCapabilityMatrix(
            objective="Market Discovery",
            target="opportunities",
            discover_jobs=True,
            discover_companies=True,
            confidence_score=75,
            supports_native_freshness=False,  # Actor doesn't support native freshness filtering via URL currently
            supports_native_sort=False,
            supports_max_items=True,
            supports_company_search=False,
            supports_semantic_search=False,
            supports_experience_filter=False,
            supports_remote_filter=False,
            supports_employment_filter=False,
            supports_location_filter=True
        )

    def initialize(self) -> None:
        pass

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
        caps = self.get_capabilities()
        
        location_slug = task.locations[0].lower().replace(" ", "-")
        role_slug = task.canonical_query.lower().replace(" ", "-")
        
        search_url = f"https://wellfound.com/role/l/{role_slug}/{location_slug}"
        
        if not caps.supports_experience_filter and task.experience_profile:
            warnings.append(f"[{self.name}] Actor ignored experience_profile {task.experience_profile}. Relying on downstream Normalizer.")
        if not caps.supports_remote_filter and "Remote" in task.work_modes:
            warnings.append(f"[{self.name}] Actor natively ignored remote work_modes. Relying on downstream Normalizer.")

        run_input = {
            "urls": [{"url": search_url}],
            "limit": task.budget.get("max_results", 50),
        }
        
        if not caps.supports_native_freshness:
            warnings.append(f"[{self.name}] Actor ignored maxAgeDays/freshness. Relying on downstream normalization filtering.")

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
