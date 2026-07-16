import os
import sys
import time
import signal
from typing import Optional
from src.config.settings import settings
from src.discovery.queue.sqlite_queue import SQLiteQueue
from src.discovery.pipeline.repositories.metrics_repository import MetricsRepository
from src.core.repositories.manager import RepositoryManager
from src.core.repositories.interfaces import WorkerState, WorkerType

class BaseWorker:
    def __init__(self, name: str, db_path: str = None, repos: Optional[RepositoryManager] = None):
        self.name = name
        self.db_path = db_path or settings.db_path
        self.repos = repos or RepositoryManager(self.db_path)
        self.worker_id = f"{name.lower()}-{os.getpid()}"
        
        # Legacy components
        self.queue = SQLiteQueue(self.db_path)
        self.metrics = MetricsRepository(self.db_path)
        
        self.running = True
        self._init_state()
        self._register_signals()

    def _determine_worker_type(self) -> WorkerType:
        n = self.name.lower()
        if "discovery" in n:
            return WorkerType.DISCOVERY
        if "verification" in n:
            return WorkerType.VERIFICATION
        if "crawler" in n or "board" in n:
            return WorkerType.CRAWLER
        if "apply" in n:
            return WorkerType.APPLY
        if "learning" in n:
            return WorkerType.LEARNING
        return WorkerType.CRAWLER # fallback

    def _register_signals(self):
        def handle_shutdown(sig, frame):
            # Graceful teardown
            self.stop("Received shutdown signal")
            sys.exit(0)
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

    def _init_state(self):
        self.repos.worker.register_worker(
            worker_id=self.worker_id,
            worker_name=self.name,
            worker_type=self._determine_worker_type(),
            pid=os.getpid()
        )
        self.repos.worker.heartbeat(self.worker_id, WorkerState.STARTING)

    def heartbeat(self, jobs_processed=0, failure_increment=0, last_error=None):
        # Update operational metrics
        self.metrics.update_operational_metric(f"{self.name}:heartbeat", time.time())
        self.metrics.update_operational_metric(f"{self.name}:status", "RUNNING")
        
        self.repos.worker.heartbeat(self.worker_id, WorkerState.RUNNING)
        if jobs_processed > 0 or failure_increment > 0:
            self.repos.worker.record_progress(self.worker_id, jobs_processed=jobs_processed, failures=failure_increment)
        
        if last_error:
            self.repos.worker.record_error(self.worker_id, str(last_error))

    def stop(self, reason: str = "Graceful shutdown"):
        self.running = False
        self.metrics.update_operational_metric(f"{self.name}:status", "STOPPED")
        self.repos.worker.stop_worker(self.worker_id, reason_for_exit=reason)
