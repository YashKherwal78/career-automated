from typing import Optional, Dict, Any
import time
import uuid
import datetime

from src.core.repositories.base import BaseRepository
from src.core.repositories.interfaces import ICompanySchedulingRepository

class SQLiteSchedulingRepository(BaseRepository, ICompanySchedulingRepository):
    def reserve_due_company(self, worker_id: str, provider_id: Optional[str] = None, lock_duration: int = 300, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        token = f"{worker_id}-{uuid.uuid4().hex[:8]}"
        now_epoch = now_dt.timestamp()
        expiry_epoch = now_epoch + lock_duration
        
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            provider_clause = f"AND provider_id = {p}" if provider_id else ""
            sql_select = f"""
                SELECT id FROM ats_registry
                WHERE status = 'ACTIVE'
                {provider_clause}
                AND (reservation_token IS NULL OR reserved_until <= {p})
                AND (next_check_at IS NULL OR next_check_at <= {p})
                ORDER BY priority + (({p} - coalesce(next_check_at, {p})) / 3600.0) DESC,
                         (CASE WHEN last_job_sync IS NULL THEN 0 ELSE 1 END) ASC,
                         next_check_at ASC
                LIMIT 1
            """
            select_params = []
            if provider_id:
                select_params.append(provider_id)
            select_params.extend([now_epoch, now_epoch, now_epoch, now_epoch])
            
            cur = conn.execute(sql_select, select_params)
            row_sel = cur.fetchone()
            if not row_sel:
                return None
            
            target_id = row_sel[0] if isinstance(row_sel, (tuple, list)) else row_sel["id"]
            
            conn.execute(f"""
                UPDATE ats_registry
                SET reservation_token = {p}, reserved_by = {p}, reserved_until = {p}, lease_token = {p}, lease_epoch = lease_epoch + 1
                WHERE id = {p}
            """, (token, worker_id, expiry_epoch, token, target_id))
            
            cur_res = conn.execute(f"SELECT * FROM ats_registry WHERE id = {p}", (target_id,))
            row = cur_res.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur_res.description], row))
            return None

    def renew_company_lease(self, company_id: str, lease_token: str, duration_seconds: int = 300, tx: Optional[Any] = None) -> bool:
        now_epoch = datetime.datetime.now(datetime.timezone.utc).timestamp()
        new_expiry = now_epoch + duration_seconds
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cur = conn.execute(f"""
                UPDATE ats_registry
                SET reserved_until = {p}
                WHERE company_id = {p} AND lease_token = {p}
            """, (new_expiry, company_id, lease_token))
            return cur.rowcount > 0

    def mark_company_completed(self, company_id: str, lease_token: str, interval_seconds: int = 86400, tx: Optional[Any] = None) -> None:
        now_epoch = datetime.datetime.now(datetime.timezone.utc).timestamp()
        next_check_epoch = now_epoch + interval_seconds
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            conn.execute(f'''
                UPDATE ats_registry
                SET last_job_sync = {p},
                    last_successful_crawl = {p},
                    failure_count = 0,
                    reservation_token = NULL,
                    reserved_by = NULL,
                    reserved_until = NULL,
                    next_check_at = {p}
                WHERE company_id = {p} AND (lease_token = {p} OR reservation_token = {p})
            ''', (now_epoch, now_epoch, next_check_epoch, company_id, lease_token, lease_token))

    def mark_company_failed(self, company_id: str, lease_token: str, backoff_schedule: list, tx: Optional[Any] = None) -> None:
        now_epoch = datetime.datetime.now(datetime.timezone.utc).timestamp()
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cursor = conn.execute(f"SELECT failure_count FROM ats_registry WHERE company_id = {p}", (company_id,))
            row = cursor.fetchone()
            failures = (row["failure_count"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) if row else 0
            failures += 1

            index = min(failures - 1, len(backoff_schedule) - 1)
            backoff = backoff_schedule[index]
            next_check_epoch = now_epoch + backoff
            
            conn.execute(f'''
                UPDATE ats_registry
                SET failure_count = {p},
                    reservation_token = NULL,
                    reserved_by = NULL,
                    reserved_until = NULL,
                    next_check_at = {p}
                WHERE company_id = {p} AND (lease_token = {p} OR reservation_token = {p})
            ''', (failures, next_check_epoch, company_id, lease_token, lease_token))


class PostgresSchedulingRepository(BaseRepository, ICompanySchedulingRepository):
    def reserve_due_company(self, worker_id: str, provider_id: Optional[str] = None, lock_duration: int = 300, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        token = f"{worker_id}-{uuid.uuid4().hex[:8]}"
        expiry_dt = now_dt + datetime.timedelta(seconds=lock_duration)
        
        with self.transaction() as conn:
            params = []
            provider_filter = ""
            if provider_id:
                provider_filter = "AND provider_id = %s"
                params.append(provider_id)
            params.extend([now_dt, now_dt, now_dt, now_dt])
            params.extend([token, worker_id, expiry_dt, token])

            cursor = conn.execute(f'''
                WITH reserved AS (
                    SELECT id FROM ats_registry
                    WHERE status = 'ACTIVE'
                      {provider_filter}
                      AND (reservation_token IS NULL OR reserved_until_tz <= %s)
                      AND (next_check_at_tz IS NULL OR next_check_at_tz <= %s)
                    ORDER BY priority + (EXTRACT(EPOCH FROM (%s - coalesce(next_check_at_tz, %s))) / 3600.0) DESC,
                             (CASE WHEN last_job_sync IS NULL THEN 0 ELSE 1 END) ASC,
                             next_check_at_tz ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE ats_registry a
                SET reservation_token = %s,
                    reserved_by = %s,
                    reserved_until_tz = %s,
                    lease_token = %s,
                    lease_epoch = lease_epoch + 1
                FROM reserved r
                WHERE a.id = r.id
                RETURNING a.*
            ''', tuple(params))
            row = cursor.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cursor.description], row))
            return None

    def renew_company_lease(self, company_id: str, lease_token: str, duration_seconds: int = 300, tx: Optional[Any] = None) -> bool:
        new_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=duration_seconds)
        with self.transaction() as conn:
            cur = conn.execute("""
                UPDATE ats_registry
                SET reserved_until_tz = %s
                WHERE company_id = %s AND lease_token = %s
            """, (new_expiry, company_id, lease_token))
            return cur.rowcount > 0

    def mark_company_completed(self, company_id: str, lease_token: str, interval_seconds: int = 86400, tx: Optional[Any] = None) -> None:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_epoch = now_dt.timestamp()
        next_check_dt = now_dt + datetime.timedelta(seconds=interval_seconds)
        with self.transaction() as conn:
            conn.execute('''
                UPDATE ats_registry
                SET last_job_sync = %s,
                    last_successful_crawl = %s,
                    failure_count = 0,
                    reservation_token = NULL,
                    reserved_by = NULL,
                    reserved_until_tz = NULL,
                    lease_token = NULL,
                    next_check_at_tz = %s
                WHERE company_id = %s AND (lease_token = %s OR reservation_token = %s)
            ''', (now_epoch, now_epoch, next_check_dt, company_id, lease_token, lease_token))

    def mark_company_failed(self, company_id: str, lease_token: str, backoff_schedule: list, tx: Optional[Any] = None) -> None:
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        with self.transaction() as conn:
            cursor = conn.execute("SELECT failure_count FROM ats_registry WHERE company_id = %s", (company_id,))
            row = cursor.fetchone()
            failures = (row["failure_count"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) if row else 0
            failures += 1

            index = min(failures - 1, len(backoff_schedule) - 1)
            backoff = backoff_schedule[index]
            next_check_dt = now_dt + datetime.timedelta(seconds=backoff)
            
            conn.execute('''
                UPDATE ats_registry
                SET failure_count = %s,
                    reservation_token = NULL,
                    reserved_by = NULL,
                    reserved_until_tz = NULL,
                    lease_token = NULL,
                    next_check_at_tz = %s
                WHERE company_id = %s AND (lease_token = %s OR reservation_token = %s)
            ''', (failures, next_check_dt, company_id, lease_token, lease_token))


def get_scheduling_repository() -> ICompanySchedulingRepository:
    from src.runtime.postgres.connection import USE_POSTGRES
    if USE_POSTGRES:
        return PostgresSchedulingRepository()
    return SQLiteSchedulingRepository()
