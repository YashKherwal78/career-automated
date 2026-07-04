import time
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from src.discovery.backends.discovery_cache import DiscoveryCache

@dataclass
class StandardJob:
    """The standard schema that all V2 providers must output."""
    company: str
    role: str
    location: str
    remote_hybrid_onsite: str
    experience_required: str
    skills: List[str]
    job_description: str
    ats_type: str
    application_url: str
    source: str
    date_posted: str

@dataclass
class ProviderCapabilities:
    requires_api_key: bool = False
    rate_limit_per_minute: int = 60
    supports_pagination: bool = False
    supports_incremental_sync: bool = False
    supports_remote_jobs: bool = False
    supports_search_filters: bool = False

@dataclass
class ProviderStatus:
    healthy: bool = True
    last_success: Optional[str] = None
    average_response_time: float = 0.0
    jobs_found: int = 0
    failure_reason: Optional[str] = None
    
    _total_response_time: float = 0.0
    _runs: int = 0
    
    def record_success(self, runtime: float, jobs: int):
        self.healthy = True
        self.last_success = datetime.utcnow().isoformat()
        self.jobs_found += jobs
        self.failure_reason = None
        self._runs += 1
        self._total_response_time += runtime
        self.average_response_time = self._total_response_time / self._runs
        
    def record_failure(self, reason: str):
        self.healthy = False
        self.failure_reason = reason

class BaseProvider(ABC):
    def __init__(self):
        self.status = ProviderStatus()
        self.capabilities = self._get_capabilities()
        self.cache = DiscoveryCache()
        
    @property
    def name(self) -> str:
        return self.__class__.__name__
        
    @property
    def pipeline_type(self) -> str:
        return getattr(self, '_pipeline_type', 'PIPELINE_A')

    @abstractmethod
    def _get_capabilities(self) -> ProviderCapabilities:
        """Return the capabilities of this provider."""
        pass

    def validate_configuration(self) -> bool:
        """Validate if the provider is correctly configured and ready to run."""
        # For now, default to True. Child classes can override to check API keys.
        return True

    def discover_jobs(self, last_sync_timestamp: Optional[str] = None) -> List[StandardJob]:
        if not self.validate_configuration():
            self.status.record_failure("Configuration validation failed (e.g. missing API key)")
            return []
            
        start = time.time()
        try:
            jobs = self._discover_jobs_internal(last_sync_timestamp)
            self.status.record_success(time.time() - start, len(jobs))
            return jobs
        except Exception as e:
            self.status.record_failure(str(e))
            return []
            
    def discover_company_jobs(self, company_name: str, last_sync_timestamp: Optional[str] = None) -> List[StandardJob]:
        return []
        
    def discover_startups(self) -> List[str]:
        return []

    @abstractmethod
    def _discover_jobs_internal(self, last_sync_timestamp: Optional[str]) -> List[StandardJob]:
        """Implemented by child classes to fetch and map jobs to StandardJob."""
        pass
