import os
import sys
import time
import subprocess
import signal
import logging
from src.config.settings import settings
from src.core.repositories.manager import RepositoryManager
from src.core.repositories.interfaces import WorkerState, WorkerType

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

def get_worker_type(name: str) -> WorkerType:
    if "Discovery" in name:
        return WorkerType.DISCOVERY
    if "Verification" in name:
        return WorkerType.VERIFICATION
    if "Crawler" in name or "JobBoard" in name:
        return WorkerType.CRAWLER
    if "FastApi" in name or "Scheduler" in name:
        return WorkerType.SCHEDULER
    return WorkerType.SCHEDULER

class PipelineScheduler:
    def __init__(self, db_path: str = settings.db_path):
        self.db_path = db_path
        self.repos = RepositoryManager(self.db_path)
        self.processes = {}
        self.running = True
        self.scheduler_id = f"scheduler_{os.getpid()}"
        
        # Run database migrations before starting any workers
        logger.info("Running database migrations...")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        result = subprocess.run([sys.executable, "src/database/migrate.py"], env=env, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
        else:
            logger.info(f"Migration completed: {result.stdout}")
            
        # Register the scheduler itself
        self.repos.worker.register_worker(
            worker_id=self.scheduler_id,
            worker_name="PipelineScheduler",
            worker_type=WorkerType.SCHEDULER,
            pid=os.getpid()
        )
        self.repos.worker.heartbeat(worker_id=self.scheduler_id, state=WorkerState.RUNNING)

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

        proc = subprocess.Popen(cmd, env=env)
        self.processes[name] = (proc, args)

        worker_id = f"{name}_{proc.pid}"
        self.repos.worker.register_worker(
            worker_id=worker_id,
            worker_name=name,
            worker_type=get_worker_type(name),
            pid=proc.pid
        )
        self.repos.worker.heartbeat(worker_id=worker_id, state=WorkerState.RUNNING)

    def monitor(self):
        logger.info("Scheduler monitoring loop active.")
        # Initial launch
        for name, args in WorkerRegistry.get_registered_workers():
            self.start_worker(name, args)

        while self.running:
            try:
                time.sleep(5)
                
                # Update scheduler heartbeat
                self.repos.worker.heartbeat(worker_id=self.scheduler_id, state=WorkerState.RUNNING)
                
                for name, (proc, args) in list(self.processes.items()):
                    worker_id = f"{name}_{proc.pid}"
                    exit_code = proc.poll()
                    if exit_code is not None:
                        logger.warning(f"Worker {name} exited with code {exit_code}. Restarting...")
                        
                        # Record error and stop worker
                        self.repos.worker.record_error(worker_id=worker_id, error_message=f"Process exited with code {exit_code}")
                        self.repos.worker.stop_worker(worker_id=worker_id, reason_for_exit=f"Crashed with code {exit_code}")

                        self.start_worker(name, args)
                    else:
                        # Update heartbeat pulse in states table for uvicorn (others update their own)
                        if name == "FastApiServer":
                            self.repos.worker.heartbeat(worker_id=worker_id, state=WorkerState.RUNNING)

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
            worker_id = f"{name}_{proc.pid}"
            proc.terminate()
            try:
                proc.wait(timeout=5)
                reason = "Terminated gracefully"
            except subprocess.TimeoutExpired:
                logger.warning(f"Process {name} did not exit. Killing...")
                proc.kill()
                reason = "Killed forcefully"
            
            # Stop the worker in repository
            self.repos.worker.stop_worker(worker_id=worker_id, reason_for_exit=reason)

        logger.info("All managed processes terminated.")
        self.repos.worker.stop_worker(worker_id=self.scheduler_id, reason_for_exit="Scheduler shutdown")

if __name__ == "__main__":
    scheduler = PipelineScheduler()
    
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}. Stopping scheduler...")
        scheduler.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    scheduler.monitor()
