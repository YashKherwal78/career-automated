import time
import os
from typing import Optional, Dict, Any
from src.core.repositories.base import BaseRepository

try:
    import psutil
except ImportError:
    psutil = None

class MetricsRepository(BaseRepository):
    def update_worker_progress(self, worker_id: str, last_checkpoint: int, batch_number: int, processed_total: int, start_time: float, worker_version: str, git_commit: str) -> None:
        now = time.time()
        elapsed = now - start_time
        rate = round(processed_total / (elapsed / 60.0), 1) if elapsed > 0 else 0.0
        
        TOTAL_COMPANIES = 57422
        remaining = TOTAL_COMPANIES - processed_total
        eta_seconds = (remaining / (processed_total / elapsed)) if processed_total > 0 else 0.0
        eta_str = f"{int(eta_seconds // 3600)}h {int((eta_seconds % 3600) // 60)}m"

        cpu_usage = 0.0
        memory_usage = 0.0
        if psutil:
            try:
                process = psutil.Process(os.getpid())
                memory_usage = round(process.memory_info().rss / (1024 * 1024), 2)
                cpu_usage = round(psutil.cpu_percent(), 2)
            except Exception:
                pass

        with self.transaction() as conn:
            p = conn.dialect.placeholder()
            
            upsert = conn.dialect.upsert(
                table="worker_progress",
                conflict_columns=["worker_name"],
                update_columns=[
                    "status", "last_checkpoint", "batch_number", "processed",
                    "companies_per_min", "eta", "memory_usage", "cpu_usage",
                    "git_commit", "updated_at"
                ]
            )
            
            conn.execute(f"""
                INSERT INTO worker_progress (
                    worker_name, status, last_checkpoint, batch_number, processed, 
                    success_count, failure_count, retry_count, companies_per_min, eta,
                    memory_usage, cpu_usage, worker_version, git_commit, updated_at
                ) VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
                {upsert}
            """, (
                worker_id, "RUNNING", str(last_checkpoint), batch_number, processed_total,
                processed_total, 0, 0, rate, eta_str,
                memory_usage, cpu_usage, worker_version, git_commit, now
            ))

            conn.execute(f"""
                INSERT INTO worker_metrics (timestamp, worker, processed, rate, cpu, memory, eta)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})
            """, (now, worker_id, processed_total, rate, cpu_usage, memory_usage, eta_seconds))

