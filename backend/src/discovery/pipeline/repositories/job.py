import dataclasses
import json
import logging
import sqlite3
import time
from typing import List, Tuple
from src.discovery.models import CanonicalJob
from src.discovery.pipeline.repositories.base import BaseRepository
from src.discovery.eligibility_fields import (
    compute_is_senior,
    compute_is_india_eligible,
    compute_remote_type_normalized,
    compute_posted_at_ts,
)
from src.discovery.html_text import strip_html

logger = logging.getLogger("JobRepository")

def is_postgres() -> bool:
    try:
        from src.runtime.postgres.connection import USE_POSTGRES
        return USE_POSTGRES
    except ImportError:
        return False

class JobRepository(BaseRepository):
    def _init_db(self):
        # Use existing normalized_jobs table created by migrations
        pass

    def upsert_and_diff(self, jobs: List[CanonicalJob], board_id: str, synced_at: float) -> Tuple[int, int, int, int]:
        """
        Takes the new canonical jobs, diffs against existing active jobs for the board/company.
        Returns (inserted, updated, archived, previous_jobs).
        """
        inserted = 0
        updated = 0
        archived = 0

        # Single defensive pass, here rather than in each of the ~55
        # per-provider connectors/normalizers -- confirmed real
        # (2026-08-25): only 14 of them actually called strip_html() on
        # their raw description before this point (Workable among the
        # ones that didn't), so unstripped HTML was reaching
        # normalized_jobs.description, the embedding text, and search_vector
        # for the rest. This is the one place every CanonicalJob passes
        # through before storage/embedding regardless of source, so fixing
        # it here covers all of them at once instead of auditing and
        # patching every connector individually (and any new connector
        # added later gets this for free). strip_html() is idempotent on
        # already-plain text, so this is a no-op for the 14 that already
        # clean their own descriptions. CanonicalJob is a frozen dataclass,
        # hence dataclasses.replace() rather than in-place mutation.
        jobs = [dataclasses.replace(j, description=strip_html(j.description)) for j in jobs]

        if not jobs:
            company_id = board_id
            with self.get_connection() as conn:
                is_sqlite = getattr(conn, "_is_sqlite", isinstance(conn, sqlite3.Connection))
                if not is_sqlite and is_postgres():
                    cur = conn.execute(
                        "UPDATE normalized_jobs SET status = 'CLOSED', closed_at = NOW() WHERE company_id = %s AND status = 'ACTIVE'",
                        (company_id,)
                    )
                    archived = cur.rowcount if hasattr(cur, 'rowcount') else 0
                else:
                    cur = conn.execute(
                        "UPDATE normalized_jobs SET status = 'CLOSED', closed_at = datetime('now') WHERE company_id = ? AND status = 'ACTIVE'",
                        (company_id,)
                    )
                    archived = cur.rowcount if hasattr(cur, 'rowcount') else 0
                conn.commit()
            return (0, 0, archived, archived)
            
        company_id = jobs[0].company_id

        # 1. Get all active job hashes for this company
        with self.get_connection() as conn:
            is_sqlite = getattr(conn, "_is_sqlite", isinstance(conn, sqlite3.Connection))
            if is_sqlite or not is_postgres():
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("SELECT job_hash FROM normalized_jobs WHERE company_id = ? AND status = 'ACTIVE'", (company_id,))
                active_hashes = {row['job_hash'] if isinstance(row, sqlite3.Row) or isinstance(row, dict) else row[0] for row in cursor.fetchall()}
            else:
                cursor = conn.execute("SELECT job_hash FROM normalized_jobs WHERE company_id = %s AND status = 'ACTIVE'", (company_id,))
                active_hashes = {row['job_hash'] if isinstance(row, dict) else row[0] for row in cursor.fetchall()}
            
        current_hashes = set()

        # Inline v1 embedding at discovery time (2026-08-24): embed only the
        # genuinely NEW jobs in this sync batch, computed once as a single
        # batched embed_batch() call (not per-job) -- same pattern
        # embedding_backfill_worker.py already uses for the existing
        # backlog. Deliberately v1 (bge-small) only, not v2/nomic -- v1 has
        # a hard ~512-token effective context regardless of input length
        # (silently truncated, not attended over), so unlike nomic there's
        # no risk of one long JD blowing up batch memory the way the
        # 2026-08-24 OOM incident did (see memory
        # vm-crash-incident-2026-08-24-oom). Plain title+description text,
        # not the JDExtractor-enriched version the backfill worker uses --
        # that extra per-job CPU cost stays out of the crawler's hot path;
        # the backfill worker remains responsible for the pre-existing
        # backlog and never re-visits a job once `embedding` is set here
        # (get_jobs_missing_embedding() filters on embedding IS NULL).
        # Wrapped in try/except so a model hiccup degrades to "embedding
        # stays NULL, backfill worker picks it up later" rather than
        # blocking job discovery/storage entirely.
        embedding_by_hash: dict = {}
        if is_postgres():
            new_jobs = [j for j in jobs if j.identity.get_hash() not in active_hashes]
            if new_jobs:
                try:
                    from src.discovery.embeddings import embed_batch, job_embedding_text
                    texts = [job_embedding_text(j.title, j.description) for j in new_jobs]
                    vectors = embed_batch(texts)
                    embedding_by_hash = {
                        j.identity.get_hash(): v for j, v in zip(new_jobs, vectors)
                    }
                except Exception as e:
                    logger.warning(f"Inline embedding failed for board={board_id}, company={company_id}: {e}")

        with self.get_connection() as conn:
            is_sqlite = getattr(conn, "_is_sqlite", isinstance(conn, sqlite3.Connection))
            for job in jobs:
                job_hash = job.identity.get_hash()
                current_hashes.add(job_hash)

                is_new = job_hash not in active_hashes
                if is_new:
                    inserted += 1
                else:
                    updated += 1

                if not is_sqlite and is_postgres():
                    # Structured eligibility fields (migration 049, see the
                    # 2026-08-24 indexing audit) -- computed once here
                    # instead of live regex/text-parsing on every hybrid-
                    # search request. Same rules the live query used, just
                    # moved off the request path; see eligibility_fields.py.
                    is_senior = compute_is_senior(job.title)
                    is_india_eligible = compute_is_india_eligible(job.location)
                    remote_type_normalized = compute_remote_type_normalized(job.remote_type, job.location)
                    posted_at_ts = compute_posted_at_ts(job.posted_at)
                    # None for existing/updated jobs (never computed above)
                    # AND for new jobs where embedding failed -- ON CONFLICT
                    # doesn't touch the embedding column below, so this
                    # value only ever actually lands for a genuine first
                    # insert; a failed-embedding NULL just leaves the row
                    # for embedding_backfill_worker.py to pick up later.
                    embedding_vec = embedding_by_hash.get(job_hash)

                    conn.execute("""
                        INSERT INTO normalized_jobs (
                            job_id, provider_job_id, company_id, provider, title, location,
                            remote_type, employment_type, department, salary_min, salary_max,
                            currency, posted_at, apply_url, description, job_hash, status,
                            raw_payload_json, is_senior, is_india_eligible,
                            remote_type_normalized, posted_at_ts, embedding
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, 'ACTIVE',
                            %s, %s, %s,
                            %s, %s, %s::vector
                        )
                        ON CONFLICT(job_id) DO UPDATE SET
                            title=excluded.title,
                            location=excluded.location,
                            apply_url=excluded.apply_url,
                            description=excluded.description,
                            status='ACTIVE',
                            raw_payload_json=excluded.raw_payload_json,
                            is_senior=excluded.is_senior,
                            is_india_eligible=excluded.is_india_eligible,
                            remote_type_normalized=excluded.remote_type_normalized,
                            posted_at_ts=excluded.posted_at_ts
                    """, (
                        job_hash, job.identity.external_job_id or job_hash, job.company_id, job.identity.provider, job.title, job.location,
                        job.remote_type, job.employment_type, job.department, job.salary_min, job.salary_max,
                        job.salary_currency, job.posted_at, job.apply_url, job.description, job_hash,
                        json.dumps(job.raw_payload), is_senior, is_india_eligible,
                        remote_type_normalized, posted_at_ts, embedding_vec
                    ))
                else:
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
                now = time.time()
                for h in missing_hashes:
                    if is_postgres():
                        conn.execute("UPDATE normalized_jobs SET status = 'CLOSED', closed_at = NOW() WHERE job_hash = %s", (h,))
                    else:
                        conn.execute("UPDATE normalized_jobs SET status = 'CLOSED', closed_at = datetime('now') WHERE job_hash = ?", (h,))
            
            conn.commit()
            
        return (inserted, updated, archived, len(active_hashes))
