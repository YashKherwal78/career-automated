import json
import sqlite3
import time
from typing import List, Tuple
from src.discovery.models import CanonicalJob
from src.discovery.pipeline.repositories.base import BaseRepository

class JobRepository(BaseRepository):
    def _init_db(self):
        # Use existing normalized_jobs table created by migrations
        pass

    def upsert_and_diff(self, jobs: List[CanonicalJob], board_id: str, synced_at: float) -> Tuple[int, int, int]:
        """
        Takes the new canonical jobs, diffs against existing active jobs for the board/company.
        Returns (inserted, updated, archived).
        """
        inserted = 0
        updated = 0
        archived = 0
        
        if not jobs:
            return (0, 0, 0)
            
        company_id = jobs[0].company_id

        # 1. Get all active job hashes for this company
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT job_hash FROM normalized_jobs WHERE company_id = ? AND status = 'ACTIVE'", (company_id,))
            active_hashes = {row['job_hash'] for row in cursor.fetchall()}
            
        current_hashes = set()
        
        with self.get_connection() as conn:
            for job in jobs:
                job_hash = job.identity.get_hash()
                current_hashes.add(job_hash)
                
                is_new = job_hash not in active_hashes
                if is_new:
                    inserted += 1
                else:
                    updated += 1
                    
                conn.execute("""
                    INSERT INTO normalized_jobs (
                        job_id, provider_job_id, company_id, provider, title, location, 
                        remote_type, employment_type, department, salary_min, salary_max, 
                        currency, posted_at, apply_url, description, job_hash, status,
                        raw_payload_json
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, 'ACTIVE',
                        ?
                    )
                    ON CONFLICT(job_id) DO UPDATE SET
                        title=excluded.title,
                        location=excluded.location,
                        apply_url=excluded.apply_url,
                        description=excluded.description,
                        status='ACTIVE',
                        raw_payload_json=excluded.raw_payload_json
                """, (
                    job_hash, job.identity.external_job_id or job_hash, job.company_id, job.identity.provider, job.title, job.location,
                    job.remote_type, job.employment_type, job.department, job.salary_min, job.salary_max,
                    job.salary_currency, job.posted_at, job.apply_url, job.description, job_hash,
                    json.dumps(job.raw_payload)
                ))
            
            # Identify archived jobs
            missing_hashes = active_hashes - current_hashes
            if missing_hashes:
                archived = len(missing_hashes)
                for h in missing_hashes:
                    conn.execute("UPDATE normalized_jobs SET status = 'CLOSED', closed_at = datetime('now') WHERE job_hash = ?", (h,))
            
            conn.commit()
            
        return (inserted, updated, archived)
