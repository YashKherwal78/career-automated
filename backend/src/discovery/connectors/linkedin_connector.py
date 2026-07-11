import datetime
from typing import Dict, Any, List, Tuple
from apify_client import ApifyClient
from src.discovery.connectors.search_connector_base import SearchConnectorBase
from src.discovery.discovery_connector import ConnectorCapabilityMatrix
from src.discovery.search_planner import SearchTask
from src.common.credential_provider import CredentialFactory, Credential

class LinkedinConnector(SearchConnectorBase):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.actor_id = config.get("actor", "hKByXkMQaC5Qt9UMN")
        self.credentials = CredentialFactory.get("APIFY")

    @property
    def name(self) -> str:
        return "LinkedInConnector"

    def get_capabilities(self) -> ConnectorCapabilityMatrix:
        return ConnectorCapabilityMatrix(
            objective="Market Discovery",
            target="opportunities",
            discover_jobs=True,
            discover_companies=True,
            confidence_score=80,
            supports_native_freshness=True,
            supports_native_sort=False,
            supports_max_items=True,
            supports_company_search=True,
            supports_semantic_search=True,
            supports_experience_filter=True,
            supports_remote_filter=True,
            supports_employment_filter=True,
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
        
        freshness_map = {
            1: "r86400",
            3: "r259200",
            7: "r604800"
        }
        f_tpr = freshness_map.get(task.freshness_days, "r86400")
        
        exp_map = {"Internship": "1", "Entry": "2", "Associate": "3", "Mid": "4", "Senior": "4", "Director": "5", "Executive": "6"}
        f_e = ",".join([exp_map[e] for e in task.experience_profile if e in exp_map])
        
        wt_map = {"On-site": "1", "Remote": "2", "Hybrid": "3"}
        f_wt = ",".join([wt_map[m] for m in task.work_modes if m in wt_map])
        
        keyword_str = task.canonical_query
        search_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword_str}&location={task.locations[0]}&f_TPR={f_tpr}"
        
        if f_e:
            search_url += f"&f_E={f_e}"
        if f_wt:
            search_url += f"&f_WT={f_wt}"

        run_input = {
            "urls": [search_url],
            "maxItems": task.budget.get("max_results", 50)
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
