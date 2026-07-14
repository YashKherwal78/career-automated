from dataclasses import dataclass, field
from typing import List


@dataclass
class BoardIdentity:
    ats: str

@dataclass
class StandardBoardIdentity(BoardIdentity):
    board_token: str

    @property
    def company_identifier(self) -> str:
        return self.board_token

@dataclass
class WorkdayBoardIdentity(BoardIdentity):
    tenant: str
    site: str
    locale: str = "en-US"

@dataclass
class GreenhouseBoardIdentity(BoardIdentity):
    board_token: str

@dataclass
class LeverBoardIdentity(BoardIdentity):
    board_token: str

@dataclass
class Candidate:

    url: str
    source: str
    source_page: str
    depth: int

@dataclass
class InspectionResult:
    board_exists: bool
    job_count: int
    api_verified: bool
    canonical_company: str
    endpoint: str
    identity: BoardIdentity = None

@dataclass
class VerifiedCandidate:
    url: str
    adapter_name: str
    candidate: Candidate
    inspection: InspectionResult
    sort_key: tuple
    discovered_at: str

@dataclass
class SelectionResult:
    winner: VerifiedCandidate
    alternatives: List[VerifiedCandidate]
    reason: str



@dataclass
class Board:
    company_id: str
    identity: BoardIdentity
    endpoint: str
    provider: str
    discovered_by: str
    discovered_at: float
    last_verified_at: float
    metadata: dict = field(default_factory=dict)

@dataclass
class JobIdentity:
    provider: str
    board_id: str
    external_job_id: str = None
    fingerprint: str = None
    
    def get_hash(self) -> str:
        import hashlib
        if self.external_job_id:
            key = f"{self.provider}_{self.board_id}_{self.external_job_id}"
        elif self.fingerprint:
            key = f"{self.provider}_{self.board_id}_fp_{self.fingerprint}"
        else:
            raise ValueError("JobIdentity must have either external_job_id or fingerprint")
        return hashlib.md5(key.encode()).hexdigest()


@dataclass
class FetchResult:
    status_code: int
    payload: dict | bytes | None
    etag: str | None
    last_modified: str | None
    content_hash: str
    bytes_downloaded: int
    response_headers: dict
    request_duration_ms: int

@dataclass
class ConnectorCapability:
    pagination: str
    supports_etag: bool
    supports_last_modified: bool
    supports_content_hash: bool
    supports_incremental: bool
    supports_parallel_fetch: bool
    supports_snapshot: bool

    # New Phase 2 Capabilities
    supports_bulk_fetch: bool = False
    supports_graphql: bool = False
    requires_browser: bool = False
    requires_cookie: bool = False
    requires_js: bool = False
    supports_delta: bool = False
    supports_salary: bool = False
    supports_departments: bool = False
    supports_remote: bool = False
    supports_location: bool = False

@dataclass
class BoardSyncTask:
    board_id: str
    priority: int
    scheduled_at: float
    retry_count: int

@dataclass
class RawJob:
    company_id: str
    provider: str
    board_identity: BoardIdentity
    payload: dict

@dataclass(frozen=True)
class CanonicalJob:
    identity: JobIdentity
    company_id: str
    board_id: str
    title: str
    description: str
    location: str
    remote_type: str
    department: str
    employment_type: str
    seniority: str
    salary_min: float
    salary_max: float
    salary_currency: str
    posted_at: str
    apply_url: str
    raw_payload: dict
    normalized_at: float
    schema_version: int = 1
    normalizer_version: int = 1

