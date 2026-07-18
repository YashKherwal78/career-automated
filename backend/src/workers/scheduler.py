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
    if settings.enable_cleanup:
        WorkerRegistry.register("CleanupWorker", ["src/workers/cleanup_worker.py"])
    
    # Register OutboxPublisherWorker to run on leader/standby processes
    WorkerRegistry.register("OutboxPublisherWorker", ["src/workers/outbox_publisher.py"])

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
    if "Outbox" in name:
        return WorkerType.SCHEDULER
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
        self.is_leader = False
        self.lock_connection = None
        
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

    def try_acquire_leadership(self):
        try:
            if not self.lock_connection:
                from src.api.db import get_connection
                self.lock_connection = get_connection()
            # PostgreSQL session-level advisory lock
            cur = self.lock_connection.execute("SELECT pg_try_advisory_lock(1784300)")
            row = cur.fetchone()
            val = (row["pg_try_advisory_lock"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) if row else False
            if val:
                if not self.is_leader:
                    logger.info("Leadership acquired successfully! Operating as Leader.")
                    self.is_leader = True
            else:
                if self.is_leader:
                    logger.warning("Leadership lost! Running in standby mode.")
                    self.is_leader = False
        except Exception as e:
            logger.error(f"Error during leadership check: {e}")
            self.is_leader = False

    def run_leader_loop(self):
        if not self.is_leader:
            return
        try:
            # 1. Fetch enabled active providers
            with self.repos.company_state.transaction() as conn:
                cur = conn.execute("SELECT provider_id FROM ats_providers WHERE enabled = TRUE")
                providers = [r["provider_id"] for r in cur.fetchall()]

            # 2. For each provider, count backlog and update provider_scheduler
            for provider in providers:
                with self.repos.company_state.transaction() as conn:
                    # Count due backlog using safe TIMESTAMPTZ column next_check_at_tz
                    cur = conn.execute('''
                        SELECT COUNT(*) FROM ats_registry 
                        WHERE status = 'ACTIVE' 
                          AND provider_id = %s 
                          AND (next_check_at_tz IS NULL OR next_check_at_tz <= NOW())
                    ''', (provider,))
                    row = cur.fetchone()
                    backlog = (row["count"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) if row else 0

                    # desired_workers calculation: max(1, min(backlog // 20, 5))
                    desired = 1 if backlog > 0 else 0
                    if backlog > 20:
                        desired = min(2 + (backlog // 50), 6)

                    # Update provider_scheduler configuration
                    conn.execute('''
                        INSERT INTO provider_scheduler (provider_id, desired_workers, backlog, last_scheduler_run)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (provider_id) DO UPDATE SET 
                            desired_workers = EXCLUDED.desired_workers, 
                            backlog = EXCLUDED.backlog, 
                            last_scheduler_run = NOW()
                    ''', (provider, desired, backlog))
            logger.info("Leader scheduler loop ran successfully: quotas updated.")
        except Exception as e:
            logger.error(f"Error in leader scheduler loop: {e}")

    def start_worker(self, name: str, args: list):
        logger.info(f"Starting worker: {name} (args={args})")
        
        # Determine launch command
        if name == "FastApiServer":
            cmd = [sys.executable] + args
        else:
            cmd = [sys.executable, args[0]]
            if len(args) > 1:
                cmd.extend(args[1:])

        # Inject PYTHONPATH to ensure subprocesses find the src module
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()

        proc = subprocess.Popen(cmd, env=env)
        self.processes[name] = (proc, args)

        worker_id = f"{name}_{proc.pid}"
        self.repos.worker.register_worker(
            worker_id=worker_id,
            worker_name=name.split("_")[0], # register base name
            worker_type=get_worker_type(name),
            pid=proc.pid
        )
        self.repos.worker.heartbeat(worker_id=worker_id, state=WorkerState.RUNNING)

    def monitor(self):
        logger.info("Scheduler monitoring loop active.")
        # Initial launch of static workers
        for name, args in WorkerRegistry.get_registered_workers():
            self.start_worker(name, args)

        last_leader_check = 0.0

        while self.running:
            try:
                time.sleep(5)
                
                # Update scheduler heartbeat
                self.repos.worker.heartbeat(worker_id=self.scheduler_id, state=WorkerState.RUNNING)
                
                # Try leadership check and quota computation every 30 seconds
                now = time.time()
                if now - last_leader_check >= 30:
                    self.try_acquire_leadership()
                    self.run_leader_loop()
                    last_leader_check = now

                # Reconcile crawler workers based on desired worker counts in database
                desired_map = {}
                try:
                    with self.repos.company_state.transaction() as conn:
                        cur = conn.execute("SELECT provider_id, desired_workers FROM provider_scheduler")
                        desired_map = {r["provider_id"]: r["desired_workers"] for r in cur.fetchall()}
                except Exception as e:
                    logger.error(f"Could not read desired worker counts: {e}")

                # Monitor and restart exited static workers
                for name, (proc, args) in list(self.processes.items()):
                    if name.startswith("Crawler_"):
                        continue
                    worker_id = f"{name}_{proc.pid}"
                    exit_code = proc.poll()
                    if exit_code is not None:
                        logger.warning(f"Static worker {name} exited with code {exit_code}. Restarting...")
                        self.repos.worker.record_error(worker_id=worker_id, error_message=f"Process exited with code {exit_code}")
                        self.repos.worker.stop_worker(worker_id=worker_id, reason_for_exit=f"Crashed with code {exit_code}")
                        self.start_worker(name, args)
                    else:
                        if name == "FastApiServer":
                            self.repos.worker.heartbeat(worker_id=worker_id, state=WorkerState.RUNNING)

                # Reconcile dynamic crawler pools for enabled providers
                for provider, desired in desired_map.items():
                    # Count currently active local worker subprocesses for this provider
                    active_crawlers = []
                    for name, (proc, args) in list(self.processes.items()):
                        if name.startswith(f"Crawler_{provider}_"):
                            exit_code = proc.poll()
                            if exit_code is not None:
                                # clean up exited crawler worker
                                logger.info(f"Dynamic crawler {name} exited. Cleaning up.")
                                worker_id = f"{name}_{proc.pid}"
                                self.repos.worker.stop_worker(worker_id=worker_id, reason_for_exit=f"Finished with code {exit_code}")
                                self.processes.pop(name, None)
                            else:
                                active_crawlers.append(name)

                    # Scale up if needed
                    while len(active_crawlers) < desired:
                        import uuid
                        uid = uuid.uuid4().hex[:6]
                        key = f"Crawler_{provider}_{uid}"
                        args = ["src/workers/job_crawler_worker.py", "--provider", provider]
                        self.start_worker(key, args)
                        active_crawlers.append(key)

                    # Scale down if desired workers decreased
                    while len(active_crawlers) > desired:
                        to_remove = active_crawlers.pop()
                        proc, args = self.processes[to_remove]
                        logger.info(f"Scaling down: terminating dynamic crawler {to_remove}")
                        proc.terminate()
                        try:
                            proc.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                        worker_id = f"{to_remove}_{proc.pid}"
                        self.repos.worker.stop_worker(worker_id=worker_id, reason_for_exit="Scaled down by manager")
                        self.processes.pop(to_remove, None)

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

        if self.lock_connection:
            try:
                self.lock_connection.execute("SELECT pg_advisory_unlock(1784300)")
                self.lock_connection.close()
            except Exception:
                pass

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
