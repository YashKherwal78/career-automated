from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum, auto
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

# ---------------------------------------------------------------------------
# Candidate Evaluation Models
# ---------------------------------------------------------------------------

class CandidateCategory(str, Enum):
    """Coarse category for a discovered URL — used as primary scoring tier."""
    DIRECT_ATS     = "direct_ats"       # hostname matches a known ATS (greenhouse.io etc.)
    CAREERS_PAGE   = "careers_page"     # path == /careers
    JOBS_PAGE      = "jobs_page"        # path == /jobs
    LIKELY_CAREERS = "likely_careers"   # /join-us, /work-with-us, /open-roles
    HOMEPAGE       = "homepage"         # path is /
    SOCIAL         = "social"           # linkedin.com, glassdoor.com, indeed.com
    BLOG_NEWS      = "blog_news"        # /blog, /press, external news sites
    UNKNOWN        = "unknown"

@dataclass
class CandidateEvidence:
    """
    Rich, explainable evidence object attached to each candidate before scoring.
    Every scoring signal must be traceable here so Mission Control can surface it.
    """
    source: str                                    # which pipeline stage produced this
    category: CandidateCategory = CandidateCategory.UNKNOWN
    ats_hostname: Optional[str] = None             # e.g. "greenhouse.io" if direct ATS
    ats_fingerprint_on_page: bool = False          # found ATS JS/iframe on the careers page
    robots_mentions_jobs: bool = False             # robots.txt disallows /careers or similar
    sitemap_has_jobs: bool = False                 # sitemap.xml contains /jobs entries
    redirect_target: Optional[str] = None         # URL that this candidate 302-ed to
    redirect_is_ats: bool = False                 # redirect resolved to a known ATS domain
    historical_verified: bool = False             # was this URL verified in a previous run?
    score_breakdown: Dict[str, int] = field(default_factory=dict)  # label -> points

@dataclass
class DiscoveryPolicy:
    """
    All scoring weights and thresholds are configurable here — nothing is hardcoded.
    Future: Mission Control can expose sliders that write back to this config.
    """
    # --- Score bonuses ---
    direct_ats_bonus:    int = 100
    careers_page_bonus:  int = 40
    jobs_page_bonus:     int = 30
    likely_careers_bonus:int = 20
    homepage_bonus:      int = 5
    ats_fingerprint_bonus: int = 20
    robots_bonus:        int = 15
    sitemap_bonus:       int = 10
    redirect_ats_bonus:  int = 80
    historical_bonus:    int = 25

    # --- Score penalties ---
    social_penalty:      int = -40
    blog_penalty:        int = -60
    unknown_penalty:     int = -10

    # --- Verification gate ---
    # Threshold starts at 0.0 (collection mode) — C1C will calibrate the real value
    # from production data once we have enough predicted vs actual pairs.
    min_confidence_threshold: float = 0.0   # effectively disabled until calibrated by C1C
    max_k:                   int = 5         # C1B.6: histogram shows cliff after top-5; K=3 recall=60%
    confidence_gap_stop:     float = 0.20    # C1B.6: gap between direct_ats (0.40) and careers (0.16) is 0.24


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
