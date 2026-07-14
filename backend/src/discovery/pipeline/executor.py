import asyncio
import logging
from dataclasses import dataclass
from src.discovery.pipeline.sync_session import BoardSyncSession

logger = logging.getLogger("ConnectorExecutor")

@dataclass
class ExecutionResult:
    status: str
    latency_ms: int
    bytes_downloaded: int
    jobs_found: int
    errors: list
    retry_hint: str

class ConnectorExecutor:
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_tasks = 0
        
    @property
    def available_capacity(self) -> int:
        return self.max_concurrent - self.active_tasks
        
    async def fetch(self, session: BoardSyncSession) -> ExecutionResult:
        """Executes a single session under the concurrency semaphore."""
        async with self.semaphore:
            self.active_tasks += 1
            try:
                await session.execute()
                stats = session.stats
                return ExecutionResult(
                    status="SUCCESS" if stats.get("success") else "FAILED",
                    latency_ms=stats.get("duration_ms", 0),
                    bytes_downloaded=stats.get("bytes_downloaded", 0),
                    jobs_found=stats.get("jobs_extracted", 0),
                    errors=[stats.get("error_message")] if stats.get("error_message") else [],
                    retry_hint="RETRYABLE" if stats.get("http_status", 200) in (429, 503) else "PERMANENT"
                )
            except Exception as e:
                logger.error(f"Executor failed for {session.board.endpoint}: {e}")
                return ExecutionResult(
                    status="ERROR",
                    latency_ms=0,
                    bytes_downloaded=0,
                    jobs_found=0,
                    errors=[str(e)],
                    retry_hint="RETRYABLE"
                )
            finally:
                self.active_tasks -= 1
