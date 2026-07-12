import os
import sys
import time
import subprocess
import signal
import logging
from src.config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Scheduler")

class WorkerRegistry:
    _registry = []

    @classmethod
    def register(cls, worker_name: str, script_args: list):
        cls._registry.append((worker_name, script_args))

    @classmethod
    def get_registered_workers(cls) -> list:
        return cls._registry

# ── Pipeline A workers ─────────────────────────────────────────────────────
if settings.enable_pipeline_a:
    if settings.enable_discovery:
        WorkerRegistry.register("CompanyDiscoveryWorker", ["src/workers/company_discovery_worker.py"])
        WorkerRegistry.register("SeedDiscoveryWorker", ["src/workers/seed_discovery_worker.py"])
    if settings.enable_verification:
        WorkerRegistry.register("EndpointVerificationWorker", ["src/workers/endpoint_verification_worker.py"])
    if settings.enable_crawler:
        WorkerRegistry.register("JobCrawlerWorker", ["src/workers/job_crawler_worker.py"])
    if settings.enable_cleanup:
        WorkerRegistry.register("CleanupWorker", ["src/workers/cleanup_worker.py"])

# ── Pipeline B workers ─────────────────────────────────────────────────────
if settings.enable_pipeline_b:
    WorkerRegistry.register("JobBoardWorker", ["src/workers/job_board_worker.py"])

if not os.environ.get("NO_API"):
    port = os.environ.get("PORT", "8000")
    WorkerRegistry.register("FastApiServer", ["-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", port])

class PipelineScheduler:
    def __init__(self, db_path: str = settings.db_path):
        self.db_path = db_path
        self.processes = {}
        self.running = True
        
        # Run database migrations before starting any workers
        logger.info("Running database migrations...")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        result = subprocess.run(["python3", "src/database/migrate.py"], env=env, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
        else:
            logger.info(f"Migration completed: {result.stdout}")
            
        self._init_db()

    def _init_db(self):
        from src.api.db import get_connection
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
            conn.commit()
        finally:
            conn.close()

    def start_worker(self, name: str, args: list):
        logger.info(f"Starting worker: {name} (args={args})")
        
        # Determine launch command
        if name == "FastApiServer":
            cmd = [sys.executable] + args
        else:
            cmd = [sys.executable, args[0]]

        # Inject PYTHONPATH to ensure subprocesses find the src module
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()

        # Redirect worker logs to stdout for Railway logging
        # Log state
        proc = subprocess.Popen(cmd, env=env)
        self.processes[name] = (proc, args)

        # Log state
        from src.api.db import get_connection, is_postgres
        conn = get_connection()
        try:
            if is_postgres():
                conn.execute('''
                    INSERT INTO worker_states (worker_name, pid, status, started_at, heartbeat, jobs_processed, failures, last_error)
                    VALUES (%s, %s, 'RUNNING', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0, 0, NULL)
                    ON CONFLICT (worker_name) DO UPDATE SET
                        pid = EXCLUDED.pid,
                        status = EXCLUDED.status,
                        started_at = EXCLUDED.started_at,
                        heartbeat = EXCLUDED.heartbeat,
                        jobs_processed = EXCLUDED.jobs_processed,
                        failures = EXCLUDED.failures,
                        last_error = EXCLUDED.last_error
                ''', (name, proc.pid))
            else:
                conn.execute('''
                    INSERT OR REPLACE INTO worker_states (worker_name, pid, status, started_at, heartbeat, jobs_processed, failures, last_error)
                    VALUES (?, ?, 'RUNNING', datetime('now'), datetime('now'), 0, 0, NULL)
                ''', (name, proc.pid))
            conn.commit()
        finally:
            conn.close()

    def monitor(self):
        logger.info("Scheduler monitoring loop active.")
        # Initial launch
        for name, args in WorkerRegistry.get_registered_workers():
            self.start_worker(name, args)

        while self.running:
            try:
                time.sleep(5)
                for name, (proc, args) in list(self.processes.items()):
                    # Check if subprocess is still running
                    exit_code = proc.poll()
                    if exit_code is not None:
                        logger.warning(f"Worker {name} exited with code {exit_code}. Restarting...")
                        
                        # Increment failures in states table
                        from src.api.db import get_connection, is_postgres
                        conn = get_connection()
                        try:
                            if is_postgres():
                                conn.execute('''
                                    UPDATE worker_states 
                                    SET failures = failures + 1,
                                        last_error = %s
                                    WHERE worker_name = %s
                                ''', (f"Process exited with code {exit_code}", name))
                            else:
                                conn.execute('''
                                    UPDATE worker_states 
                                    SET failures = failures + 1,
                                        last_error = ?
                                    WHERE worker_name = ?
                                ''', (f"Process exited with code {exit_code}", name))
                            conn.commit()
                        finally:
                            conn.close()

                        self.start_worker(name, args)
                    else:
                        # Update heartbeat pulse in states table for uvicorn (others update their own)
                        if name == "FastApiServer":
                            from src.api.db import get_connection, is_postgres
                            conn = get_connection()
                            try:
                                if is_postgres():
                                    conn.execute('''
                                        UPDATE worker_states 
                                        SET heartbeat = CURRENT_TIMESTAMP
                                        WHERE worker_name = %s
                                    ''', (name,))
                                else:
                                    conn.execute('''
                                        UPDATE worker_states 
                                        SET heartbeat = datetime('now')
                                        WHERE worker_name = ?
                                    ''', (name,))
                                conn.commit()
                            finally:
                                conn.close()

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in scheduler monitor loop: {e}")

        self.shutdown()

    def shutdown(self):
        logger.info("Shutdown initiated. Terminating all processes...")
        self.running = False
        for name, (proc, args) in self.processes.items():
            logger.info(f"Terminating process {name} (PID: {proc.pid})")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {name} did not exit. Killing...")
                proc.kill()
            
            # Update database status
            from src.api.db import get_connection, is_postgres
            conn = get_connection()
            try:
                if is_postgres():
                    conn.execute('UPDATE worker_states SET status = \'STOPPED\' WHERE worker_name = %s', (name,))
                else:
                    conn.execute('UPDATE worker_states SET status = "STOPPED" WHERE worker_name = ?', (name,))
                conn.commit()
            finally:
                conn.close()

        logger.info("All managed processes terminated.")

if __name__ == "__main__":
    scheduler = PipelineScheduler()
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}. Stopping scheduler...")
        scheduler.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    scheduler.monitor()
