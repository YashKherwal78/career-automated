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
        with self.transaction() as conn:
            params = []
            provider_filter = ""
            if provider_id:
                provider_filter = "AND provider_id = %s"
                params.append(provider_id)
            params.extend([now_dt, now_dt])
            params.extend([token, worker_id, expiry_dt, token])

            cursor = conn.execute(f'''
                WITH reserved AS (
                    SELECT id FROM ats_registry
                    WHERE status = 'ACTIVE'
                      {provider_filter}
                      AND (reservation_token IS NULL OR reserved_until_tz <= %s)
                      AND (next_check_at_tz IS NULL OR next_check_at_tz <= %s)
                    ORDER BY priority DESC,
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

    def mark_completed(self, company_id: str, token: str, interval: int, tx: Optional[Any] = None) -> None:
        import datetime
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        next_check_dt = now_dt + datetime.timedelta(seconds=interval)
        with self.transaction() as conn:
            conn.execute('''
                UPDATE ats_registry
                SET last_job_sync = %s,
                    last_successful_crawl = %s,
                    failure_count = 0,
                    reservation_token = NULL,
                    reserved_by = NULL,
                    reserved_until_tz = NULL,
                    next_check_at_tz = %s
                WHERE company_id = %s AND lease_token = %s
            ''', (now_dt, now_dt, next_check_dt, company_id, token))

    def mark_failed(self, company_id: str, token: str, backoff_schedule: list, tx: Optional[Any] = None) -> None:
        import datetime
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
                    next_check_at_tz = %s
                WHERE company_id = %s AND lease_token = %s
            ''', (failures, next_check_dt, company_id, token))

