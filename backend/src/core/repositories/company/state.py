from typing import Optional, Dict, Any
from src.core.repositories.interfaces import ICompanyStateRepository
from src.core.repositories.base import BaseRepository
from src.core.repositories.registry_resolver import RegistryResolver

class CompanyStateRepository(BaseRepository, ICompanyStateRepository):
    def get_state(self, provider: str, company_id: str, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        with self.transaction() as conn:
            table_name = RegistryResolver.state_table(provider)
            p = conn.dialect.placeholder()
            cur = conn.execute(f"SELECT * FROM {table_name} WHERE company_id = {p}", (company_id,))
            row = cur.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row))
            return None
                
    def acquire_lock(self, provider: str, company_id: str, worker_id: str, tx: Optional[Any] = None) -> bool:
        with self.transaction() as conn:
            table_name = RegistryResolver.state_table(provider)
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            cur = conn.execute(f"""
                UPDATE {table_name} 
                SET status='CRAWLING', crawl_lock=1, locked_at={now}, worker_id={p}
                WHERE company_id={p} AND crawl_lock=0
            """, (worker_id, company_id))
            return cur.rowcount > 0
                
    def update_success(self, provider: str, company_id: str, updates: Dict[str, Any], tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            table_name = RegistryResolver.state_table(provider)
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            # SQLite specific datetime function datetime('now', ...) needs abstraction or we just pass pre-computed values.
            # But wait, next_crawl_offset logic is usually better handled in Python if not fully abstracted.
            # However, I see datetime('now', ?) in the query. I will replace this with python pre-computation.
            import time
            next_crawl_ts = time.time() + float(updates['next_crawl_offset'])
            
            conn.execute(f"""
                UPDATE {table_name} 
                SET status='QUEUED', crawl_lock=0, locked_at=NULL, worker_id=NULL,
                    previous_jobs={p}, current_jobs={p}, job_delta={p}, last_success={now}, 
                    consecutive_failures=0, total_success=total_success+1,
                    next_crawl={p}, health_score=100.0,
                    crawl_tier={p}, crawl_interval_hours={p}, rolling_churn_percent={p}, crawls_in_current_tier={p},
                    decision_reason={p}, last_tier_change={updates.get('last_tier_change', now)}
                WHERE company_id={p}
            """, (
                updates['previous_jobs'], updates['current_jobs'], updates['job_delta'], 
                next_crawl_ts,
                updates['crawl_tier'], updates['crawl_interval_hours'], updates['rolling_churn_percent'], 
                updates['crawls_in_current_tier'], updates['decision_reason'], company_id
            ))
                
    def update_failure(self, provider: str, company_id: str, updates: Dict[str, Any], tx: Optional[Any] = None) -> None:
        import datetime
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        next_check_val = updates.get('next_check_at', 0.0)
        if isinstance(next_check_val, (int, float)):
            next_check_dt = datetime.datetime.fromtimestamp(next_check_val, datetime.timezone.utc)
        else:
            next_check_dt = now_dt + datetime.timedelta(hours=2)
            
        with self.transaction() as conn:
            conn.execute("""
                UPDATE ats_registry 
                SET status=%s,
                    failure_count=failure_count+1,
                    next_check_at_tz=%s
                WHERE company_id=%s
            """, (
                updates['status'].value if hasattr(updates['status'], 'value') else updates['status'], 
                next_check_dt, company_id
            ))

    def reserve_due_board(self, worker_id: str, provider_id: Optional[str] = None, lock_duration: int = 300, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        import time
        import uuid
        import datetime
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        token = f"{worker_id}-{uuid.uuid4().hex[:8]}"
        expiry_dt = now_dt + datetime.timedelta(seconds=lock_duration)
        now_epoch = now_dt.timestamp()
        expiry_epoch = now_epoch + lock_duration
        with self.transaction() as conn:
            is_sqlite_conn = getattr(conn, 'is_sqlite', False) or getattr(getattr(conn, '_conn', None), 'is_sqlite', False) or 'SQLite' in conn.__class__.__name__
            if is_sqlite_conn:
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
            else:
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

    def mark_completed(self, company_id: str, token: str, interval_seconds: int = 86400, tx: Optional[Any] = None) -> None:
        import datetime
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_epoch = now_dt.timestamp()
        next_check_epoch = now_epoch + interval_seconds
        
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            if conn.is_sqlite if hasattr(conn, 'is_sqlite') else ('SQLite' in conn.__class__.__name__):
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
                ''', (now_epoch, now_epoch, next_check_epoch, company_id, token, token))
            else:
                next_check_dt = now_dt + datetime.timedelta(seconds=interval_seconds)
                conn.execute(f'''
                    UPDATE ats_registry
                    SET last_job_sync = {p},
                        last_successful_crawl = {p},
                        failure_count = 0,
                        reservation_token = NULL,
                        reserved_by = NULL,
                        reserved_until_tz = NULL,
                        next_check_at_tz = {p}
                    WHERE company_id = {p} AND (lease_token = {p} OR reservation_token = {p})
                ''', (now_epoch, now_epoch, next_check_dt, company_id, token, token))

    def mark_failed(self, company_id: str, token: str, backoff_schedule: list, tx: Optional[Any] = None) -> None:
        import datetime
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        now_epoch = now_dt.timestamp()
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cursor = conn.execute(f"SELECT failure_count FROM ats_registry WHERE company_id = {p}", (company_id,))
            row = cursor.fetchone()
            failures = (row["failure_count"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) if row else 0
            failures += 1

            index = min(failures - 1, len(backoff_schedule) - 1)
            backoff = backoff_schedule[index]
            
            if conn.is_sqlite if hasattr(conn, 'is_sqlite') else ('SQLite' in conn.__class__.__name__):
                next_check_epoch = now_epoch + backoff
                conn.execute(f'''
                    UPDATE ats_registry
                    SET failure_count = {p},
                        reservation_token = NULL,
                        reserved_by = NULL,
                        reserved_until = NULL,
                        next_check_at = {p}
                    WHERE company_id = {p} AND (lease_token = {p} OR reservation_token = {p})
                ''', (failures, next_check_epoch, company_id, token, token))
            else:
                next_check_dt = now_dt + datetime.timedelta(seconds=backoff)
                conn.execute(f'''
                    UPDATE ats_registry
                    SET failure_count = {p},
                        reservation_token = NULL,
                        reserved_by = NULL,
                        reserved_until_tz = NULL,
                        next_check_at_tz = {p}
                    WHERE company_id = {p} AND (lease_token = {p} OR reservation_token = {p})
                ''', (failures, next_check_dt, company_id, token, token))
