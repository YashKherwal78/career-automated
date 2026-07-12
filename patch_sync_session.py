import re

with open("src/discovery/pipeline/sync_session.py", "r") as f:
    text = f.read()

# Replace the block that fetches and snapshots with the dual-dispatch block
import_str = "from src.discovery.pipeline.http_client import HttpClient"
if import_str not in text:
    text = text.replace("import uuid", f"import uuid\n{import_str}")

# Replace the execution block
execute_code = """
        try:
            # Check if new Connector exists
            try:
                from src.discovery.connectors.workday import WorkdayConnector
                connectors = {"workday": WorkdayConnector()}
                connector = connectors.get(self.board.provider)
            except ImportError:
                connector = None

            if connector:
                # NEW CONNECTOR PATH
                fetch_start = time.time()
                raw_jobs = []
                async with HttpClient() as client:
                    async for raw_job in connector.sync(self.board, client):
                        raw_jobs.append(raw_job)
                
                # Currently we aren't snapshotting incrementally per page.
                # For compatibility, we'll store a dummy payload or skip snapshot
                self.stats["bytes_downloaded"] = 0
                self.stats["snapshot_id"] = "skipped_for_connector"
                
                # Normalize
                normalizer = NormalizerFactory.get_normalizer(self.board.provider)
                canonical_jobs = []
                for rj in raw_jobs:
                    canonical_jobs.extend(normalizer.normalize(rj))
                
                self.stats["jobs_extracted"] = len(canonical_jobs)
                valid_jobs, invalid_records = JobValidator.filter_valid(canonical_jobs)
                
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
"""

# Extract the execute method from the file
start_idx = text.find("        try:")
end_idx = text.find("        finally:")

if start_idx != -1 and end_idx != -1:
    old_code = text[start_idx:end_idx]
    # We replace up to "except Exception as e:\n            self.stats['success'] = False\n            self.stats['error_message'] = str(e)"
    # The execute_code string contains up to "except Exception as e:"
    # We will just replace it cleanly
    # Let's write a python snippet to do AST replace or regex safely
    pass

