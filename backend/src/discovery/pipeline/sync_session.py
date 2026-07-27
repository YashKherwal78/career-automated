import time
import uuid
import sys
import traceback
from typing import Dict, Any, List
from src.discovery.models import Board, RawJob, CanonicalJob, FetchResult
from src.discovery.pipeline.repositories.evidence import EvidenceRepository
from src.discovery.pipeline.repositories.sync import SyncRepository
from src.discovery.pipeline.repositories.job import JobRepository
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.pipeline.job_validator import JobValidator
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.pipeline.schema_detector import SchemaDetector
from src.discovery.pipeline.evidence_scorer import EvidenceScorer
from src.config.settings import settings

from src.discovery.pipeline.exceptions import (
    ConnectorNotFoundError,
    TimeoutError,
    RateLimitError,
    CrawlerException,
    DatabaseException
)

class BoardSyncSession:
    def __init__(self, board: Board, db_path: str = "boards.db"):
        self.board = board
        self.session_id = str(uuid.uuid4())
        self.started_at = time.time()
        self.evidence_repo = EvidenceRepository(db_path)
        self.sync_repo = SyncRepository(db_path)
        self.job_repo = JobRepository(db_path)
        self.session_payloads = []
        
        self.stats = {
            "id": self.session_id,
            "board_id": board.endpoint, # using endpoint as ID for now
            "provider": board.provider,
            "connector_name": f"{board.provider}_rest", # To be extracted correctly if possible
            "started_at": self.started_at,
            "finished_at": None,
            "duration_ms": 0,
            "http_status": 200,
            "bytes_downloaded": 0,
            "jobs_extracted": 0,
            "jobs_inserted": 0,
            "jobs_updated": 0,
            "jobs_archived": 0,
            "success": False,
            "error_message": None,
            "exception_type": None,
            "schema_hash": None,
            "connector_version_id": "v1" # Placeholder
        }

    async def execute(self):
        try:
            # Check if Connector exists
            connector = ConnectorRegistry.get(self.board.provider)
            if not connector:
                raise ConnectorNotFoundError(f"Connector not found for provider {self.board.provider}")

            fetch_start = time.time()
            raw_jobs = []
            
            try:
                async with HttpClient() as client:
                    async for item in connector.sync(self.board, client):
                        if isinstance(item, FetchResult):
                            self.stats["bytes_downloaded"] += item.bytes_downloaded
                            if item.content_hash:
                                self.board.metadata["content_hash"] = item.content_hash
                            # Buffer payload instead of writing to disk immediately
                            if item.payload:
                                self.session_payloads.append(item.payload)
                                if getattr(item, "status_code", None):
                                    self.stats["http_status"] = item.status_code
                        else:
                            raw_jobs.append(item)
            except Exception as e:
                err_msg = str(e).lower()
                if "timeout" in err_msg or "timeouterror" in err_msg:
                    raise TimeoutError(str(e)) from e
                elif "429" in err_msg or "rate limit" in err_msg or "rate_limited" in err_msg:
                    self.stats["http_status"] = 429
                    raise RateLimitError(str(e)) from e
                else:
                    raise CrawlerException(str(e)) from e
            
            # Compute schema hash on the first payload if available
            if self.session_payloads:
                self.stats["schema_hash"] = SchemaDetector.compute_schema_hash(self.session_payloads[0])
                
            if raw_jobs:
                normalizer = NormalizerFactory.get_normalizer(self.board.provider)
                canonical_jobs = []
                for rj in raw_jobs:
                    canonical_jobs.extend(normalizer.normalize(rj))
                
                self.stats["jobs_extracted"] = len(canonical_jobs)
                valid_jobs, invalid_records = JobValidator.filter_valid(canonical_jobs)
            else:
                self.stats["jobs_extracted"] = 0
                valid_jobs = []

            b_id = f"{self.board.identity.tenant}_{self.board.identity.site}" if hasattr(self.board.identity, 'tenant') else getattr(self.board.identity, 'board_token', 'unknown')
            try:
                inserted, updated, archived, prev_jobs = self.job_repo.upsert_and_diff(valid_jobs, b_id, self.started_at)
            except Exception as e:
                raise DatabaseException(f"Database error during upsert_and_diff: {e}") from e

            self.stats["jobs_inserted"] = inserted
            self.stats["jobs_updated"] = updated
            self.stats["jobs_archived"] = archived
            self.stats["success"] = True
            
        except Exception as e:
            self.stats["success"] = False
            self.stats["error_message"] = str(e)
            self.stats["exception_type"] = type(e).__name__
            self.stats["stack_trace"] = "".join(traceback.format_exception(*sys.exc_info()))
            traceback.print_exc()
            
        finally:
            self.stats["finished_at"] = time.time()
            self.stats["duration_ms"] = (self.stats["finished_at"] - self.stats["started_at"]) * 1000
            
            self._finalize_evidence()
            
        return self.stats

    def _finalize_evidence(self):
        # 1. Determine Yield Regression
        rolling_mean, rolling_count = self.sync_repo.get_board_statistics(self.board.endpoint)
        is_low_yield = False
        if rolling_count > 0 and rolling_mean > 10:
            if self.stats["jobs_extracted"] < (0.1 * rolling_mean):
                is_low_yield = True

        # 2. Evaluate Evidence Score
        # For simplicity in V1, we assume schema hasn't changed unless we actively verify it.
        # Ideally, we query `crawl_evidence` for the existing schema hash, but we use the hash as the key anyway.
        score, reasons = EvidenceScorer.evaluate(self.stats, schema_changed=False, is_low_yield=is_low_yield)
        outcome_category = EvidenceScorer.determine_category(reasons)
        
        # 3. Store Evidence if required
        if score >= settings.evidence_score_threshold:
            for payload in self.session_payloads:
                self.evidence_repo.save_evidence(
                    crawl_id=self.stats["id"],
                    board_id=self.board.endpoint,
                    provider=self.board.provider,
                    category=outcome_category,
                    reasons=",".join(reasons),
                    score=score,
                    schema_hash=self.stats["schema_hash"],
                    endpoint_family="rest", # Default
                    expires_at=time.time() + (settings.evidence_retention_days * 86400),
                    payload=payload
                )
        elif self.stats["success"] and self.session_payloads:
            # Check if Reference exists, if not, save it
            # This is O(N) if we don't cache it, but fast enough for now
            refs = self.evidence_repo.get_reference_payloads(self.board.provider)
            hashes = {r["schema_hash"] for r in refs}
            if self.stats["schema_hash"] not in hashes:
                self.evidence_repo.save_evidence(
                    crawl_id=self.stats["id"],
                    board_id=self.board.endpoint,
                    provider=self.board.provider,
                    category="REFERENCE",
                    reasons="INITIAL_REFERENCE",
                    score=100,
                    schema_hash=self.stats["schema_hash"],
                    endpoint_family="rest", 
                    expires_at=0, # Never expires
                    payload=self.session_payloads[0] # Only need one
                )
                
        # 4. Save Metadata & Outcome
        self.sync_repo.record_sync(self.stats, outcome_category)
