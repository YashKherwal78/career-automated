import json
import sqlite3
import time
from typing import List, Tuple
from src.discovery.models import CanonicalJob
from src.core.repositories.base import BaseRepository
from src.core.repositories.interfaces import IJobRepository

class JobRepository(BaseRepository, IJobRepository):
    def _init_db(self):
        # Use existing normalized_jobs table created by migrations
        pass

    @property
    def _profile(self):
        if not hasattr(self, "_cached_profile"):
            try:
                from src.discovery.jie.candidate_profile import CandidateProfile
                self._cached_profile = CandidateProfile.from_yaml()
            except Exception:
                from src.discovery.jie.candidate_profile import CandidateProfile
                self._cached_profile = CandidateProfile()
        return self._cached_profile

    @property
    def _hard_reject(self):
        if not hasattr(self, "_cached_hard_reject"):
            from src.discovery.hard_reject_filter import HardRejectFilter
            self._cached_hard_reject = HardRejectFilter()
        return self._cached_hard_reject

    @property
    def _intent_filter(self):
        if not hasattr(self, "_cached_intent_filter"):
            from src.discovery.intent_filter import IntentFilter
            self._cached_intent_filter = IntentFilter()
        return self._cached_intent_filter

    def get_jobs(self, page: int=1, page_size: int=50, provider: str=None, company: str=None, status: str="ACTIVE", min_score: float=None, pipeline: str="A", location: str=None, remote_type: str=None, employment_type: str=None, seniority: str=None, min_salary: float=None, sort_by: str="newest", tx=None):
        from src.api.db import json_extract
        import json
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            json_company = json_extract('n.raw_payload_json', '$.company')
            query = f"""
                SELECT COALESCE(i.canonical_name, {json_company}, n.company_id) AS canonical_name,
                       n.job_id, n.title, 0 as job_score, n.provider, '{{}}' as score_breakdown,
                       0.0 as match_score, 0.0 as priority_score, 0.0 as scoring_confidence,
                       '' as recommendation_reason, 'NEW' as application_status,
                       n.location, n.remote_type as remote, n.employment_type,
                       n.salary_min, n.salary_max, n.posted_at, n.apply_url,
                       n.description, n.status
                FROM normalized_jobs n
                LEFT JOIN company_identities i ON n.company_id = i.company_id
                WHERE n.status = {p}
            """
            params = [status]

            job_board_providers = ["linkedin", "google_jobs", "wellfound", "indeed"]
            provider_placeholders = ",".join([p] * len(job_board_providers))
            if pipeline == "B":
                query += f" AND n.provider IN ({provider_placeholders})"
                params.extend(job_board_providers)
            else:
                query += f" AND n.provider NOT IN ({provider_placeholders})"
                params.extend(job_board_providers)

            if provider:
                query += f" AND n.provider = {p}"
                params.append(provider)
            if company:
                query += f" AND (n.company_id LIKE {p} OR COALESCE(i.canonical_name, {json_company}, '') LIKE {p})"
                params.extend([f"%{company}%", f"%{company}%"])
            if location:
                query += f" AND n.location LIKE {p}"
                params.append(f"%{location}%")
            if remote_type:
                query += f" AND n.remote_type = {p}"
                params.append(remote_type)
            if employment_type:
                query += f" AND n.employment_type = {p}"
                params.append(employment_type)
            if min_salary is not None:
                query += f" AND (n.salary_max >= {p} OR n.salary_min >= {p})"
                params.extend([min_salary, min_salary])

            limit = conn.dialect.create_limit(2000)
            query += f" ORDER BY n.posted_at DESC {limit}"
            c = conn.execute(query, tuple(params))
            raw_jobs = [dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in c.description], row)) for row in c.fetchall()]

            for j in raw_jobs:
                try:
                    j["score_breakdown"] = json.loads(j["score_breakdown"] or "[]")
                except Exception:
                    j["score_breakdown"] = []

            profile = self._profile
            passed, rejected, _ = self._hard_reject.filter_batch(raw_jobs, profile)
            scored_jobs, _ = self._intent_filter.score_batch(passed, profile)

            if min_score is not None:
                scored_jobs = [j for j in scored_jobs if j.get("intent_score", 0.0) >= min_score / 100.0]

            if sort_by == "score":
                scored_jobs.sort(key=lambda x: x.get("intent_score", 0.0), reverse=True)
            else:
                scored_jobs.sort(key=lambda x: (x.get("posted_at") or "", x.get("intent_score", 0.0)), reverse=True)

            offset = (page - 1) * page_size
            return scored_jobs[offset : offset + page_size]

    def get_job(self, job_id: str, tx=None) -> dict | None:
        from src.api.db import json_extract
        import json
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            json_company = json_extract('n.raw_payload_json', '$.company')
            query = f"""
                SELECT COALESCE(i.canonical_name, {json_company}, n.company_id) AS canonical_name,
                       n.job_id, n.title, 0 as job_score, n.provider, '{{}}' as score_breakdown,
                       0.0 as match_score, 0.0 as priority_score, 0.0 as scoring_confidence,
                       '' as recommendation_reason, 'NEW' as application_status,
                       n.description, n.location, n.remote_type as remote,
                       n.salary_min, n.salary_max, n.apply_url, n.posted_at
                FROM normalized_jobs n
                LEFT JOIN company_identities i ON n.company_id = i.company_id
                WHERE n.job_id = {p}
            """
            c = conn.execute(query, (job_id,))
            row = c.fetchone()
            if not row:
                return None
            j = dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in c.description], row))
            try:
                j["score_breakdown"] = json.loads(j["score_breakdown"] or "[]")
            except Exception:
                j["score_breakdown"] = []
            return j

    def upsert_and_diff(self, jobs: List[CanonicalJob], board_id: str, synced_at: float, tx=None) -> Tuple[int, int, int, int]:
        """
        Takes the new canonical jobs, diffs against existing active jobs for the board/company.
        Returns (inserted, updated, archived, previous_jobs).
        """
        inserted = 0
        updated = 0
        archived = 0
        
        if not jobs:
            return (0, 0, 0)
            
        company_id = jobs[0].company_id

        # 1. Get all active job hashes for this company
        with self.get_connection() as conn:
            p = conn.dialect.placeholder()
            
            # Using dict row factory safely
            if hasattr(conn, 'row_factory'):
                conn.row_factory = sqlite3.Row
                
            cursor = conn.execute(f"SELECT job_hash FROM normalized_jobs WHERE company_id = {p} AND status = 'ACTIVE'", (company_id,))
            active_hashes = {row['job_hash'] if isinstance(row, dict) or hasattr(row, 'keys') else row[0] for row in cursor.fetchall()}
            
        current_hashes = set()
        
        with self.get_connection() as conn:
            p = conn.dialect.placeholder()
            upsert = conn.dialect.upsert(
                table="normalized_jobs",
                conflict_columns=["job_id"],
                update_columns=["title", "location", "apply_url", "description", "status", "raw_payload_json"]
            )
            
            for job in jobs:
                job_hash = job.identity.get_hash()
                current_hashes.add(job_hash)
                
                is_new = job_hash not in active_hashes
                if is_new:
                    inserted += 1
                else:
                    updated += 1
                    
                conn.execute(f"""
                    INSERT INTO normalized_jobs (
                        job_id, provider_job_id, company_id, provider, title, location, 
                        remote_type, employment_type, department, salary_min, salary_max, 
                        currency, posted_at, apply_url, description, job_hash, status,
                        raw_payload_json
                    ) VALUES (
                        {p}, {p}, {p}, {p}, {p}, {p},
                        {p}, {p}, {p}, {p}, {p},
                        {p}, {p}, {p}, {p}, {p}, 'ACTIVE',
                        {p}
                    )
                    {upsert}
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
                now = conn.dialect.current_timestamp()
                for h in missing_hashes:
                    conn.execute(f"UPDATE normalized_jobs SET status = 'CLOSED', closed_at = {now} WHERE job_hash = {p}", (h,))
            
        return (inserted, updated, archived, len(active_hashes))

    def load_cursor(self, provider_name: str, tx=None) -> str | None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            limit = conn.dialect.create_limit(1)
            row = conn.execute(
                f"""SELECT cursor FROM job_board_snapshots
                   WHERE provider = {p} AND status IN ('SUCCESS', 'PARTIAL')
                   ORDER BY synced_at DESC {limit}""",
                (provider_name,),
            ).fetchone()
            return row[0] if row else None

    def save_snapshot(
        self,
        provider_name: str,
        next_cursor: str | None,
        jobs_found: int,
        jobs_new: int,
        jobs_updated: int,
        companies_discovered: int,
        status: str,
        error: str | None,
        tx=None
    ):
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            now_ts = int(time.time())
            conn.execute(
                f"""INSERT INTO job_board_snapshots
                   (provider, synced_at, cursor, jobs_found, jobs_new,
                    jobs_updated, companies_discovered, status, error)
                   VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})""",
                (
                    provider_name,
                    now_ts,
                    next_cursor,
                    jobs_found,
                    jobs_new,
                    jobs_updated,
                    companies_discovered,
                    status,
                    error,
                ),
            )
