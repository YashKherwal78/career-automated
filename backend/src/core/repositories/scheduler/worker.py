from typing import Optional, Any, List, Dict
from src.core.repositories.interfaces import IWorkerRepository, WorkerState, WorkerType
from src.core.repositories.base import BaseRepository

class WorkerRepository(BaseRepository, IWorkerRepository):
    def register_worker(self, worker_id: str, worker_name: str, worker_type: WorkerType, provider: Optional[str] = None, pid: Optional[int] = None, timeout: int = 60, tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            upsert = conn.dialect.upsert(
                table="worker_states",
                conflict_columns=["worker_id"],
                update_columns=["worker_name", "worker_type", "provider", "pid", "status", "started_at", "heartbeat", "heartbeat_timeout"]
            )
            
            conn.execute(f"""
                INSERT INTO worker_states (
                    worker_id, worker_name, worker_type, provider, pid, status, 
                    started_at, heartbeat, heartbeat_timeout
                )
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {now}, {now}, {p})
                {upsert}
            """, (worker_id, worker_name, worker_type.value, provider, pid, WorkerState.STARTING.value, timeout))

    def heartbeat(self, worker_id: str, state: WorkerState, current_company_id: Optional[str] = None, current_task: Optional[str] = None, cpu_percent: Optional[float] = None, memory_mb: Optional[float] = None, tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            
            query = f"""
                UPDATE worker_states 
                SET status={p}, heartbeat={now}, updated_at={now}
            """
            params = [state.value]
            
            if current_company_id is not None:
                query += f", current_company_id={p}"
                params.append(current_company_id)
            if current_task is not None:
                query += f", current_task={p}"
                params.append(current_task)
            if cpu_percent is not None:
                query += f", cpu_percent={p}"
                params.append(cpu_percent)
            if memory_mb is not None:
                query += f", memory_mb={p}"
                params.append(memory_mb)
                
            query += f" WHERE worker_id={p}"
            params.append(worker_id)
            
            conn.execute(query, tuple(params))

    def record_progress(self, worker_id: str, jobs_processed: int = 0, jobs_found: int = 0, successes: int = 0, failures: int = 0, tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            conn.execute(f"""
                UPDATE worker_states
                SET jobs_processed = jobs_processed + {p},
                    jobs_found = jobs_found + {p},
                    successes = successes + {p},
                    failures = failures + {p},
                    updated_at = {now}
                WHERE worker_id = {p}
            """, (jobs_processed, jobs_found, successes, failures, worker_id))

    def record_error(self, worker_id: str, error_message: str, tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            conn.execute(f"""
                UPDATE worker_states
                SET last_error = {p},
                    last_error_at = {now},
                    failures = failures + 1,
                    updated_at = {now}
                WHERE worker_id = {p}
            """, (error_message, worker_id))

    def stop_worker(self, worker_id: str, reason_for_exit: str, tx: Optional[Any] = None) -> None:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            now = conn.dialect.current_timestamp()
            
            # First fetch the worker state to copy into history
            cur = conn.execute(f"SELECT * FROM worker_states WHERE worker_id={p}", (worker_id,))
            row = cur.fetchone()
            
            if row:
                row_dict = dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row))
                # Insert into worker_history
                conn.execute(f"""
                    INSERT INTO worker_history (
                        worker_id, started_at, ended_at, jobs_processed, failures, reason_for_exit
                    )
                    VALUES ({p}, {p}, {now}, {p}, {p}, {p})
                """, (
                    worker_id,
                    row_dict.get('started_at'),
                    row_dict.get('jobs_processed', 0),
                    row_dict.get('failures', 0),
                    reason_for_exit
                ))
            
            conn.execute(f"UPDATE worker_states SET status={p}, updated_at={now} WHERE worker_id={p}", (WorkerState.OFFLINE.value, worker_id))

    def get_workers(self, tx: Optional[Any] = None) -> List[Dict[str, Any]]:
        with self.transaction() as conn:
            cur = conn.execute("SELECT * FROM worker_states")
            return [dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row)) for row in cur.fetchall()]

    def get_worker_state(self, worker_id: str, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            cur = conn.execute(f"SELECT * FROM worker_states WHERE worker_id={p}", (worker_id,))
            row = cur.fetchone()
            if row:
                return dict(row) if hasattr(row, 'keys') else dict(zip([col[0] for col in cur.description], row))
            return None
