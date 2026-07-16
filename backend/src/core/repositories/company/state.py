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
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            conn.execute(f"""
                UPDATE ats_registry 
                SET status={p},
                    failure_count=failure_count+1,
                    next_check_at={p}
                WHERE company_id={p}
            """, (
                updates['status'].value if hasattr(updates['status'], 'value') else updates['status'], 
                updates.get('next_check_at', 0.0), company_id
            ))

    def reserve_due_board(self, worker_id: str, lock_duration: int = 300, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        import time
        import uuid
        now = time.time()
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            limit = conn.dialect.create_limit(1)
            cursor = conn.execute(f'''
                SELECT * FROM ats_registry
                WHERE status = 'ACTIVE'
                  AND (reservation_token IS NULL OR reserved_until <= {p})
                  AND (next_check_at IS NULL OR next_check_at <= {p})
                ORDER BY priority DESC, last_job_sync ASC
                {limit}
            ''', (now, now))

            row = cursor.fetchone()
            if not row:
                return None

            board_data = dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cursor.description], row))
            company_id = board_data["company_id"]
            token = f"{worker_id}-{uuid.uuid4().hex[:8]}"

            cursor_update = conn.execute(f'''
                UPDATE ats_registry
                SET reservation_token = {p},
                    reserved_by = {p},
                    reserved_until = {p}
                WHERE company_id = {p}
                  AND status = 'ACTIVE'
                  AND (reservation_token IS NULL OR reserved_until <= {p})
            ''', (token, worker_id, now + lock_duration, company_id, now))

            if cursor_update.rowcount > 0:
                board_data["reservation_token"] = token
                board_data["reserved_by"] = worker_id
                board_data["reserved_until"] = now + lock_duration
                return board_data
            else:
                return None

    def mark_completed(self, company_id: str, token: str, interval: int, tx: Optional[Any] = None) -> None:
        import time
        now = time.time()
        next_check = now + interval
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            conn.execute(f'''
                UPDATE ats_registry
                SET last_job_sync = {p},
                    last_successful_crawl = {p},
                    failure_count = 0,
                    reservation_token = NULL,
                    reserved_by = NULL,
                    reserved_until = 0.0,
                    next_check_at = {p}
                WHERE company_id = {p} AND reservation_token = {p}
            ''', (now, now, next_check, company_id, token))

    def mark_failed(self, company_id: str, token: str, backoff_schedule: list, tx: Optional[Any] = None) -> None:
        import time
        now = time.time()
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cursor = conn.execute(f"SELECT failure_count FROM ats_registry WHERE company_id = {p}", (company_id,))
            row = cursor.fetchone()
            failures = row[0] if row else 0
            failures += 1

            index = min(failures - 1, len(backoff_schedule) - 1)
            backoff = backoff_schedule[index]
            next_check = now + backoff

            conn.execute(f'''
                UPDATE ats_registry
                SET failure_count = {p},
                    reservation_token = NULL,
                    reserved_by = NULL,
                    reserved_until = 0.0,
                    next_check_at = {p}
                WHERE company_id = {p} AND reservation_token = {p}
            ''', (failures, next_check, company_id, token))

