from src.system.logger import setup_logger
logger = setup_logger('dispatcher')
from typing import Dict, Any

from src.applications.adapters.base_adapter import ApplicationResult

class ApplicationDispatcher:
    def __init__(self, profile_manager=None, rag_client=None, llm_router=None):
        self.profile_manager = profile_manager
        self.rag_client = rag_client
        self.llm_router = llm_router
        
        # Load adapters lazily to avoid circular imports and playwright overhead
        self._adapters = {}
        
    # connector name -> (module path, class name), mirroring the discovery
    # crawler's ConnectorRegistry: adding a new ATS is a one-line entry here
    # plus a new handler/adapter pair, nothing else in this file changes.
    _ADAPTER_REGISTRY = {
        "greenhouse": ("src.applications.adapters.greenhouse_adapter", "GreenhouseAdapter"),
        "lever": ("src.applications.adapters.lever_adapter", "LeverAdapter"),
        "ashby": ("src.applications.adapters.ashby_adapter", "AshbyAdapter"),
    }

    def _get_adapter(self, connector: str):
        connector = connector.lower().strip()
        if connector not in self._adapters:
            entry = self._ADAPTER_REGISTRY.get(connector)
            if not entry:
                return None
            module_path, class_name = entry
            import importlib
            module = importlib.import_module(module_path)
            adapter_class = getattr(module, class_name)
            self._adapters[connector] = adapter_class(
                profile_manager=self.profile_manager,
                rag_client=self.rag_client,
                llm_router=self.llm_router
            )
        return self._adapters[connector]

    def dispatch(self, job: Dict[str, Any], resume_path: str, test_mode: bool = True) -> ApplicationResult:
        # Defaults to test_mode=True (never clicks the final submit button) —
        # this is the entry point new/automated callers reach through, so a
        # missing or accidental invocation should never risk a real
        # submission. Real applications require an explicit test_mode=False.
        connector = job.get("connector", "unknown")

        adapter = self._get_adapter(connector)
        if not adapter:
            return ApplicationResult(
                status="REVIEW_REQUIRED",
                failure_reason=f"No adapter implemented for connector: {connector}"
            )

        logger.info(f"[Dispatcher] Routing job {job.get('id')} to {connector.capitalize()}Adapter (test_mode={test_mode})")
        try:
            return adapter.apply(job, resume_path, self.profile_manager, test_mode=test_mode)
        except Exception as e:
            logger.info(f"[Dispatcher] Unhandled adapter error: {e}")
            return ApplicationResult(
                status="FAILED",
                failure_reason=f"Unhandled Adapter Exception: {str(e)}"
            )
