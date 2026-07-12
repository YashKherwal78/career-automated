import os
import sys
import time
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
        from src.api.db import get_connection, is_postgres
        conn = get_connection()
        try:
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
            if is_postgres():
                conn.execute('''
                    INSERT INTO worker_states (worker_name, pid, status, started_at, heartbeat, jobs_processed, failures, last_error)
                    VALUES (%s, %s, 'STARTING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 0, NULL)
                    ON CONFLICT (worker_name) DO UPDATE SET
                        pid = EXCLUDED.pid,
                        status = EXCLUDED.status,
                        started_at = EXCLUDED.started_at,
                        heartbeat = EXCLUDED.heartbeat,
                        jobs_processed = EXCLUDED.jobs_processed,
                        failures = EXCLUDED.failures,
                        last_error = EXCLUDED.last_error
                ''', (self.name, os.getpid()))
            else:
                conn.execute('''
                    INSERT OR REPLACE INTO worker_states (worker_name, pid, status, started_at, heartbeat, jobs_processed, failures, last_error)
                    VALUES (?, ?, 'STARTING', datetime('now'), datetime('now'), 0, 0, NULL)
                ''', (self.name, os.getpid()))
            conn.commit()
        finally:
            conn.close()

    def heartbeat(self, jobs_processed=0, failure_increment=0, last_error=None):
        # Update operational metrics
        self.metrics.update_operational_metric(f"{self.name}:heartbeat", time.time())
        self.metrics.update_operational_metric(f"{self.name}:status", "RUNNING")
        
        from src.api.db import get_connection, is_postgres
        conn = get_connection()
        try:
            if last_error:
                if is_postgres():
                    conn.execute('''
                        UPDATE worker_states 
                        SET heartbeat = CURRENT_TIMESTAMP,
                            status = 'RUNNING',
                            jobs_processed = jobs_processed + %s,
                            failures = failures + %s,
                            last_error = %s
                        WHERE worker_name = %s
                    ''', (jobs_processed, failure_increment, str(last_error), self.name))
                else:
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
                if is_postgres():
                    conn.execute('''
                        UPDATE worker_states 
                        SET heartbeat = CURRENT_TIMESTAMP,
                            status = 'RUNNING',
                            jobs_processed = jobs_processed + %s
                        WHERE worker_name = %s
                    ''', (jobs_processed, self.name))
                else:
                    conn.execute('''
                        UPDATE worker_states 
                        SET heartbeat = datetime('now'),
                            status = 'RUNNING',
                            jobs_processed = jobs_processed + ?
                        WHERE worker_name = ?
                    ''', (jobs_processed, self.name))
            conn.commit()
        finally:
            conn.close()

    def stop(self):
        self.running = False
        self.metrics.update_operational_metric(f"{self.name}:status", "STOPPED")
        from src.api.db import get_connection, is_postgres
        conn = get_connection()
        try:
            if is_postgres():
                conn.execute('UPDATE worker_states SET status = \'STOPPED\' WHERE worker_name = %s', (self.name,))
            else:
                conn.execute('UPDATE worker_states SET status = "STOPPED" WHERE worker_name = ?', (self.name,))
            conn.commit()
        finally:
            conn.close()
