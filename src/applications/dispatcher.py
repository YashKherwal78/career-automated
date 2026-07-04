import os
from typing import Dict, Any

from src.applications.adapters.base_adapter import ApplicationResult

class ApplicationDispatcher:
    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router
        
        # Load adapters lazily to avoid circular imports and playwright overhead
        self._adapters = {}
        
    def _get_adapter(self, connector: str):
        connector = connector.lower().strip()
        if connector not in self._adapters:
            if connector == "greenhouse":
                from src.applications.adapters.greenhouse_adapter import GreenhouseAdapter
                self._adapters[connector] = GreenhouseAdapter(
                    profile_manager=self.profile_manager,
                    rag_client=self.rag_client,
                    llm_router=self.llm_router
                )
            # Add Lever, Ashby, etc. here later
            else:
                return None
        return self._adapters[connector]

    def dispatch(self, job: Dict[str, Any], resume_path: str) -> ApplicationResult:
        connector = job.get("connector", "unknown")
        
        adapter = self._get_adapter(connector)
        if not adapter:
            return ApplicationResult(
                status="REVIEW_REQUIRED",
                failure_reason=f"No adapter implemented for connector: {connector}"
            )
            
        print(f"[Dispatcher] Routing job {job.get('id')} to {connector.capitalize()}Adapter")
        try:
            return adapter.apply(job, resume_path, self.profile_manager)
        except Exception as e:
            print(f"[Dispatcher] Unhandled adapter error: {e}")
            return ApplicationResult(
                status="FAILED",
                failure_reason=f"Unhandled Adapter Exception: {str(e)}"
            )
