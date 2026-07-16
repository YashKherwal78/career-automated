from src.api.db import get_connection
import sqlite3
import time
import logging
from typing import List, Dict, Optional, Any
from src.config.config import Config
from src.jobs.models import Job

logger = logging.getLogger("JobRegistry")

class JobRegistry:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._init_db()

    def _init_db(self):
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    company_id TEXT,
                    ats_type TEXT,
                    external_id TEXT,
                    title TEXT,
                    department TEXT,
                    location TEXT,
                    employment_type TEXT,
                    workplace_type TEXT,
                    posted_date TEXT,
                    updated_date TEXT,
                    apply_url TEXT,
                    description TEXT,
                    salary TEXT,
                    currency TEXT,
                    experience_level TEXT,
                    metadata TEXT,
                    job_hash TEXT,
                    status TEXT,
                    first_seen REAL,
                    last_seen REAL,
                    last_changed REAL,
                    crawl_version INTEGER,
                    miss_count INTEGER
                )
            """)
            
            # Indices for querying and conflict resolution
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_company_external ON jobs(company_id, external_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company_id ON jobs(company_id)")
            conn.commit()

    def sync_jobs(self, company_id: str, ats_type: str, crawled_jobs: List[Job], crawl_version: int):
        """
        Takes a snapshot of crawled jobs and compares them to existing jobs in the registry.
        - New jobs -> INSERT OPEN
        - Existing, hash changed -> UPDATE OPEN, reset miss_count
        - Existing, hash unchanged -> UPDATE last_seen, reset miss_count
        - Not in snapshot -> increment miss_count, if >= 2 -> UPDATE CLOSED
        """
        import json
        now = time.time()
        
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 1. Fetch existing jobs for this company
            existing_rows = cursor.execute(
                "SELECT * FROM jobs WHERE company_id = ? AND status != 'CLOSED'", 
                (company_id,)
            ).fetchall()
            
            existing_map = {row['external_id']: dict(row) for row in existing_rows}
            seen_external_ids = set()
            
            # 2. Process crawled jobs
            for job in crawled_jobs:
                seen_external_ids.add(job.external_id)
                meta_json = json.dumps(job.metadata) if job.metadata else "{}"
                
                if job.external_id not in existing_map:
                    # NEW JOB
                    cursor.execute("""
                        INSERT INTO jobs (
                            job_id, company_id, ats_type, external_id, title, department, location,
                            employment_type, workplace_type, posted_date, updated_date, apply_url,
                            description, salary, currency, experience_level, metadata, job_hash,
                            status, first_seen, last_seen, last_changed, crawl_version, miss_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job.job_id, company_id, ats_type, job.external_id, job.title, job.department,
                        job.location, job.employment_type, job.workplace_type, job.posted_date,
                        job.updated_date, job.apply_url, job.description, job.salary, job.currency,
                        job.experience_level, meta_json, job.job_hash, 'OPEN', now, now, now, crawl_version, 0
                    ))
                else:
                    existing_job = existing_map[job.external_id]
                    if existing_job['job_hash'] != job.job_hash:
                        # EXISTING, CHANGED
                        cursor.execute("""
                            UPDATE jobs SET 
                                title = ?, department = ?, location = ?, employment_type = ?,
                                workplace_type = ?, posted_date = ?, updated_date = ?, apply_url = ?,
                                description = ?, salary = ?, currency = ?, experience_level = ?,
                                metadata = ?, job_hash = ?, status = 'OPEN', last_seen = ?, last_changed = ?,
                                crawl_version = ?, miss_count = 0
                            WHERE external_id = ? AND company_id = ?
                        """, (
                            job.title, job.department, job.location, job.employment_type,
                            job.workplace_type, job.posted_date, job.updated_date, job.apply_url,
                            job.description, job.salary, job.currency, job.experience_level,
                            meta_json, job.job_hash, now, now, crawl_version, job.external_id, company_id
                        ))
                    else:
                        # EXISTING, UNCHANGED
                        cursor.execute("""
                            UPDATE jobs SET last_seen = ?, miss_count = 0, crawl_version = ?
                            WHERE external_id = ? AND company_id = ?
                        """, (now, crawl_version, job.external_id, company_id))
                        
            # 3. Handle missing jobs (not in snapshot)
            for ext_id, ext_job in existing_map.items():
                if ext_id not in seen_external_ids:
                    new_miss_count = ext_job['miss_count'] + 1
                    if new_miss_count >= 2:
                        cursor.execute("UPDATE jobs SET status = 'CLOSED', miss_count = ? WHERE external_id = ? AND company_id = ?", (new_miss_count, ext_id, company_id))
                    else:
                        cursor.execute("UPDATE jobs SET miss_count = ? WHERE external_id = ? AND company_id = ?", (new_miss_count, ext_id, company_id))
                        
            conn.commit()
            
    def get_jobs_by_company(self, company_id: str, status: str = 'OPEN') -> List[Dict]:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            rows = cursor.execute("SELECT * FROM jobs WHERE company_id = ? AND status = ?", (company_id, status)).fetchall()
            return [dict(row) for row in rows]
