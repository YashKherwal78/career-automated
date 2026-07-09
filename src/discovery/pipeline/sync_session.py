import time
import uuid
from typing import Dict, Any, List
from src.discovery.models import Board, RawJob, CanonicalJob
from src.discovery.pipeline.repositories.snapshot import SnapshotRepository
from src.discovery.pipeline.repositories.sync import SyncRepository
from src.discovery.pipeline.repositories.job import JobRepository
from src.discovery.pipeline.normalizers import NormalizerFactory
from src.discovery.pipeline.job_validator import JobValidator
from src.discovery.registry.source_registry import SourceRegistry

class BoardSyncSession:
    def __init__(self, board: Board, db_path: str = "boards.db"):
        self.board = board
        self.session_id = str(uuid.uuid4())
        self.started_at = time.time()
        self.snapshot_repo = SnapshotRepository(db_path)
        self.sync_repo = SyncRepository(db_path)
        self.job_repo = JobRepository(db_path)
        
        self.stats = {
            "id": self.session_id,
            "board_id": board.endpoint, # using endpoint as ID for now
            "snapshot_id": None,
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
            "error_message": None
        }

    async def execute(self):
        try:
            # Import everything
            from src.discovery.registry.connector_registry import ConnectorRegistry
            from src.discovery.pipeline.http_client import HttpClient
            from src.discovery.models import FetchResult
            import src.discovery.connectors.workday # ensure registration
            
            # Import old adapters to trigger registration in SourceRegistry
            import src.discovery.connectors.greenhouse
            import src.discovery.connectors.lever
            import src.discovery.connectors.workday
            import src.discovery.workers.ashby_adapter
            import src.discovery.workers.smartrecruiters_adapter
            
            # Check if new Connector exists
            connector = ConnectorRegistry.get(self.board.provider)

            if connector:
                # NEW CONNECTOR PATH
                fetch_start = time.time()
                raw_jobs = []
                snapshot_ids = []
                self.stats["bytes_downloaded"] = 0
                
                async with HttpClient() as client:
                    async for item in connector.sync(self.board, client):
                        if isinstance(item, FetchResult):
                            self.stats["bytes_downloaded"] += item.bytes_downloaded
                            if item.content_hash:
                                self.board.metadata["content_hash"] = item.content_hash
                            # Snapshot this page
                            if item.payload:
                                sid = self.snapshot_repo.save(self.board.endpoint, item.payload, self.started_at)
                                snapshot_ids.append(sid)
                        else:
                            raw_jobs.append(item)
                
                # Use the first snapshot ID or join them
                if snapshot_ids:
                    self.stats["snapshot_id"] = ",".join(snapshot_ids[:3]) # Limit display string
                    
                if raw_jobs:
                    # Normalize
                    normalizer = NormalizerFactory.get_normalizer(self.board.provider)
                    canonical_jobs = []
                    for rj in raw_jobs:
                        canonical_jobs.extend(normalizer.normalize(rj))
                    
                    self.stats["jobs_extracted"] = len(canonical_jobs)
                
                    # 5. Validate
                    valid_jobs, invalid_records = JobValidator.filter_valid(canonical_jobs)
                else:
                    self.stats["jobs_extracted"] = 0
                    valid_jobs = []
                
            else:
                # OLD ADAPTER PATH
                adapter = SourceRegistry.get_adapter(self.board.provider)
                if not adapter:
                    raise ValueError(f"Adapter not found for provider {self.board.provider}")
                    
                # 1. Fetch
                fetch_start = time.time()
                raw_data = await adapter.fetch({"url": self.board.endpoint, "company_id": "unknown"})
                
                # 2. Snapshot
                import json
                payload_size = len(json.dumps(raw_data).encode('utf-8'))
                self.stats["bytes_downloaded"] = payload_size
                snapshot_id = self.snapshot_repo.save(self.board.endpoint, raw_data, self.started_at)
                self.stats["snapshot_id"] = snapshot_id
                
                # 3. RawJob
                raw_job = adapter.discover_jobs(raw_data, board_identity=self.board.identity)
                
                # 4. Normalize
                normalizer = NormalizerFactory.get_normalizer(self.board.provider)
                canonical_jobs = normalizer.normalize(raw_job)
                self.stats["jobs_extracted"] = len(canonical_jobs)
                
                # 5. Validate
                valid_jobs, invalid_records = JobValidator.filter_valid(canonical_jobs)

            # 6. Upsert and Diff
            b_id = f"{self.board.identity.tenant}_{self.board.identity.site}" if hasattr(self.board.identity, 'tenant') else getattr(self.board.identity, 'board_token', 'unknown')
            inserted, updated, archived = self.job_repo.upsert_and_diff(valid_jobs, b_id, self.started_at)
            self.stats["jobs_inserted"] = inserted
            self.stats["jobs_updated"] = updated
            self.stats["jobs_archived"] = archived
            
            self.stats["success"] = True
            
        except Exception as e:
            self.stats["success"] = False
            self.stats["error_message"] = str(e)
            import traceback
            traceback.print_exc()
            
        finally:
            self.stats["finished_at"] = time.time()
            self.stats["duration_ms"] = (self.stats["finished_at"] - self.stats["started_at"]) * 1000
            self.sync_repo.record_sync(self.stats)
            
        return self.stats
