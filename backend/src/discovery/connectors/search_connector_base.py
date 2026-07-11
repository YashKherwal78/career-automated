from abc import abstractmethod
from typing import Dict, Any, List, Tuple
import datetime

from src.discovery.discovery_connector import DiscoveryConnector, ConnectorResult
from src.discovery.search_planner import SearchTask

class SearchConnectorBase(DiscoveryConnector):
    """
    Base class for all Search Connectors (Pipeline B1).
    Owns Adaptive Escalation and Budget Throttling.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def execute_search(self, task: SearchTask) -> Tuple[List[Any], List[str]]:
        """
        Executes the platform-specific search logic and returns (raw_jobs, warnings).
        The connector adapter is responsible for applying the 90s hard timeout and 2 page limit.
        """
        pass

    def discover(self, session_id: str, payload: Dict[str, Any]) -> ConnectorResult:
        """
        Overrides DiscoveryConnector.discover to implement Search Escalation Policy.
        payload is expected to contain a 'task' of type SearchTask.
        """
        start_time = datetime.datetime.now()
        task: SearchTask = payload.get('task')
        
        if not task:
            return ConnectorResult(
                connector_name=self.name, connector_version="1.0", connector_type="search",
                session_id=session_id, status="FAILED", started_at=start_time.isoformat(),
                finished_at=start_time.isoformat(), duration_ms=0, api_calls=0, credits_consumed=0,
                jobs_found=0, errors=["Missing SearchTask payload"]
            )
            
        jobs = []
        api_calls = 0
        status = "SUCCESS"
        errors = []
        warnings = []
        
        # Adaptive Freshness Escalation Loop
        freshness_tiers = [1, 3, 7]
        caps = self.get_capabilities()
        
        for freshness in freshness_tiers:
            task.freshness_days = freshness
            try:
                # 1. Execute Search (Platform Adapter)
                raw_jobs, search_warnings = self.execute_search(task)
                api_calls += 1
                jobs.extend(raw_jobs)
                warnings.extend(search_warnings)
                
                # If adapter warns it ignored freshness, stop escalating freshness
                if not caps.supports_native_freshness:
                    warnings.append(f"[{self.name}] Native freshness unsupported. Escalation halted.")
                    break
                
                # 2. Halt if we found enough to satisfy the budget intent
                if len(jobs) >= task.budget.get("max_results", 50):
                    break
                    
            except Exception as e:
                status = "PARTIAL_SUCCESS" if len(jobs) > 0 else "FAILED"
                errors.append(f"Escalation failed at {freshness} days: {str(e)}")
                break

        # Hard Cutoff if somehow jobs exceeded budget wildly
        if len(jobs) > task.budget.get("max_results", 50) * 2:
            warnings.append(f"[{self.name}] Exceeded budget cutoff aggressively. Truncating.")
            jobs = jobs[:task.budget.get("max_results", 50) * 2]

        end_time = datetime.datetime.now()
        duration = int((end_time - start_time).total_seconds() * 1000)
        
        # Credit Protection: Warn if duration exceeded 90s bounds significantly
        if duration > 100000:
            warnings.append(f"[{self.name}] CRITICAL: Execution exceeded 90s budget.")

        return ConnectorResult(
            connector_name=self.name,
            connector_version="1.0",
            connector_type="search",
            session_id=session_id,
            status=status,
            started_at=start_time.isoformat(),
            finished_at=end_time.isoformat(),
            duration_ms=duration,
            api_calls=api_calls,
            credits_consumed=api_calls * self.config.get("credit_cost", 1.0),
            jobs_found=len(jobs),
            jobs=jobs,
            errors=errors,
            warnings=warnings
        )
