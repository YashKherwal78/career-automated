from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from abc import ABC, abstractmethod
import hashlib

from src.discovery.models import BoardIdentity
from src.discovery.inspectors.base_inspector import SourceInspector

class FailureReason(Enum):
    PARSER_URL_PATTERN = "parser_url_pattern"
    NO_SEARCH_RESULTS = "no_search_results"
    RATE_LIMITED = "rate_limited"
    CUSTOM_DOMAIN = "custom_domain"
    NO_CAREERS_PAGE = "no_careers_page"
    ROBOTS_BLOCKED = "robots_blocked"
    INSPECTOR_FAILED = "inspector_failed"
    UNKNOWN = "unknown"

@dataclass
class DiscoveryBudget:
    max_http_requests: int
    max_latency_seconds: float
    max_search_queries: int

@dataclass
class VerificationPolicy:
    max_candidates: int = 3
    min_score: int = 20
    concurrency: int = 3
    inspect_even_if_single_candidate: bool = True

@dataclass
class Evidence:
    source: str
    weight: int
    description: str

@dataclass
class IdentityResult:
    confidence: float
    matched_signals: List[str]
    failed_signals: List[str]
    reason: str

@dataclass
class Candidate:
    url: str
    evidence: List[Evidence] = field(default_factory=list)
    parsed_identity: Optional[BoardIdentity] = None
    parser_success: bool = False
    parser_confidence: float = 0.0
    parser_reason: Optional[str] = None
    
    inspector_success: bool = False
    inspector_error: Optional[str] = None
    
    search_provider: Optional[str] = None
    search_query: Optional[str] = None
    search_rank: Optional[int] = None
    search_title: Optional[str] = None
    
    identity_result: Optional[IdentityResult] = None
    
    validator_time_ms: int = 0
    inspector_time_ms: int = 0
    
    @property
    def candidate_id(self) -> str:
        return hashlib.sha256(self.url.encode('utf-8')).hexdigest()
    
    @property
    def score(self) -> int:
        return sum(e.weight for e in self.evidence)

@dataclass
class ProbeResult:
    path: str
    status: int
    final_url: str
    latency_ms: int
    redirect_count: int
    success: bool

@dataclass
class StageTrace:
    stage: str
    success: bool
    duration_ms: int
    requests: int
    candidates_found: int
    evidence: List[str]
    urls: List[str]
    probe_results: List[ProbeResult] = field(default_factory=list)
    redirect_chains: List[List[str]] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class SourceResult:
    candidates: List[Candidate]
    trace: StageTrace
    requests_used: int
    bytes_downloaded: int

class DiscoverySource:
    async def discover(self, context) -> SourceResult:
        raise NotImplementedError

class DiscoveryPlugin(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the ATS provider (e.g. 'greenhouse', 'workday')"""
        pass
        
    @abstractmethod
    def candidate_domains(self) -> List[str]:
        """Domains used to construct URL guesses."""
        pass
        
    @abstractmethod
    def fingerprints(self) -> List[str]:
        """URL fragments or text used to identify this ATS."""
        pass
        
    @abstractmethod
    def parse_candidate(self, url: str) -> Tuple[Optional[BoardIdentity], float, Optional[str]]:
        """Parse a URL into an identity and confidence score."""
        pass
        
    @abstractmethod
    def inspector(self) -> SourceInspector:
        """Returns the specific inspector for this ATS."""
        pass
        
    @abstractmethod
    def confidence(self, evidence: Any) -> float:
        """Calculates final verification confidence from inspection evidence."""
        pass

    # --- Registry & Discovery Extensions ---
    def canonicalize(self, endpoint: str) -> str:
        """Strips unnecessary paths/locales from the endpoint before registry insertion."""
        return endpoint

    async def health_check(self, endpoint: str) -> bool:
        """Quick ping to verify the endpoint is still active."""
        return True

    async def crawl_jobs(self, endpoint: str, metadata: dict) -> Any:
        pass

    def normalize_job(self, raw_job: Any, company_id: str, endpoint: str = "") -> Any:
        pass

    def extract_metadata(self, endpoint: str) -> str:
        return "{}"

    def crawl_policy(self, last_sync: float) -> float:
        return 6 * 3600

    def supports_incremental_sync(self) -> bool:
        return False

    async def incremental_sync(self, endpoint: str, metadata: dict, sync_state: dict) -> Any:
        pass

    def recheck_policy(self, status: str) -> float:
        """Returns the number of seconds to wait before checking this endpoint again."""
        # Default: 14 days for ACTIVE, 3 days for STALE, 24 hours for FAILED
        if status == 'ACTIVE':
            return 14 * 24 * 3600
        elif status == 'STALE':
            return 3 * 24 * 3600
        return 24 * 3600

@dataclass
class VerificationResult:
    company_id: str
    company_domain: str
    company_name: str
    ats_type: str
    endpoint: str
    canonical_endpoint: str
    endpoint_hash: str
    status: str
    discovery_source: Optional[str] = None
    search_provider: Optional[str] = None
    search_query: Optional[str] = None
    search_rank: Optional[int] = None
    identity_score: float = 0.0
    inspector_score: float = 0.0
    plugin_name: str = ""
    plugin_version: str = "1.0"
    ats_metadata: str = "{}"

@dataclass
class DiscoveryResult:
    company: str
    provider: str
    candidate_url: str
    confidence: float
    strategy: str
    latency: float
    http_requests: int
    bytes_downloaded: int
    verified: bool
    identity: Optional[BoardIdentity] = None
    evidence: Any = None
    
    # New Funnel Telemetry
    candidates_generated: int = 0
    parser_accepted: int = 0
    validation_passed: int = 0
    score_passed: int = 0
    inspector_called: int = 0
    
    skipped_validation: int = 0
    skipped_score: int = 0
    skipped_budget: int = 0
