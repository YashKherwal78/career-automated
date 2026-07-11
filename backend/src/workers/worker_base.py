import os
import sys
import time
import sqlite3
import signal
from src.config.settings import settings
from src.discovery.queue.sqlite_queue import SQLiteQueue
from src.discovery.pipeline.repositories.metrics_repository import MetricsRepository

class BaseWorker:
    def __init__(self, name: str, db_path: str = None):
        self.name = name
        self.db_path = db_path or settings.db_path
        self.worker_id = f"{name.lower()}-{os.getpid()}"
        self.queue = SQLiteQueue(self.db_path)
        self.metrics = MetricsRepository(self.db_path)
        self.running = True
        self._init_state()
        self._register_signals()

    def _register_signals(self):
        def handle_shutdown(sig, frame):
            # Graceful teardown
            self.stop()
            sys.exit(0)
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)

    def _init_state(self):
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS worker_states (
                    worker_name TEXT PRIMARY KEY,
                    pid INTEGER,
                    status TEXT,
                    started_at TEXT,
                    heartbeat TEXT,
                    jobs_processed INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    last_error TEXT
                )
            ''')
            conn.execute('''
                INSERT OR REPLACE INTO worker_states (worker_name, pid, status, started_at, heartbeat, jobs_processed, failures, last_error)
                VALUES (?, ?, 'STARTING', datetime('now'), datetime('now'), 0, 0, NULL)
            ''', (self.name, os.getpid()))
            conn.commit()

    def heartbeat(self, jobs_processed=0, failure_increment=0, last_error=None):
        # Update operational metrics
        self.metrics.update_operational_metric(f"{self.name}:heartbeat", time.time())
        self.metrics.update_operational_metric(f"{self.name}:status", "RUNNING")
        
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            if last_error:
                conn.execute('''
                    UPDATE worker_states 
                    SET heartbeat = datetime('now'),
                        status = 'RUNNING',
                        jobs_processed = jobs_processed + ?,
                        failures = failures + ?,
                        last_error = ?
                    WHERE worker_name = ?
                ''', (jobs_processed, failure_increment, str(last_error), self.name))
            else:
                conn.execute('''
                    UPDATE worker_states 
                    SET heartbeat = datetime('now'),
                        status = 'RUNNING',
                        jobs_processed = jobs_processed + ?
                    WHERE worker_name = ?
                ''', (jobs_processed, self.name))
            conn.commit()

    def stop(self):
        self.running = False
        self.metrics.update_operational_metric(f"{self.name}:status", "STOPPED")
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            conn.execute('UPDATE worker_states SET status = "STOPPED" WHERE worker_name = ?', (self.name,))
            conn.commit()
