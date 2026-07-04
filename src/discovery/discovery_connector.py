from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import datetime

@dataclass
class ConnectorCapabilityMatrix:
    objective: str = "Market Discovery"
    target: str = "opportunities"
    discover_jobs: bool = False
    discover_companies: bool = False
    verify_urls: bool = False
    supports_incremental_sync: bool = False
    supports_pagination: bool = False
    supports_search: bool = False
    supports_company_registry: bool = False
    supports_search_profiles: bool = False
    requires_authentication: bool = False
    produces_official_apply_urls: bool = False
    confidence_score: int = 50
    # Search specific capabilities
    supports_native_freshness: bool = False
    supports_native_sort: bool = False
    supports_max_items: bool = False
    supports_company_search: bool = False
    supports_semantic_search: bool = False
    supports_experience_filter: bool = False
    supports_remote_filter: bool = False
    supports_employment_filter: bool = False
    supports_location_filter: bool = False

@dataclass
class ConnectorResult:
    connector_name: str
    connector_version: str
    connector_type: str
    session_id: str
    status: str  # SUCCESS | PARTIAL_SUCCESS | FAILED
    started_at: str
    finished_at: str
    duration_ms: int
    api_calls: int
    credits_consumed: float
    jobs_found: int
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

class DiscoveryConnector(ABC):
    """
    Stateless interface for all Discovery Connectors.
    All state (sessions, retries, cursors) must be stored in the Control Plane.
    """
    
    @property
    def name(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def get_capabilities(self) -> ConnectorCapabilityMatrix:
        """Defines what this connector is capable of doing."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """One-time setup (e.g. loading API keys). Raises Exception if config is missing."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verifies API endpoints are reachable or credentials are valid."""
        pass

    @abstractmethod
    def discover(self, session_id: str, payload: Dict[str, Any]) -> ConnectorResult:
        """
        Executes discovery and returns a fully populated ConnectorResult containing raw opportunities 
        and connector execution metadata.
        """
        pass

    @abstractmethod
    def metrics(self) -> Dict[str, Any]:
        """Returns static metrics or configuration details for this connector type."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Cleanup logic if any."""
        pass
