import os
import sys
import time
import csv
import logging
import json
import subprocess
from urllib.parse import urlparse
from src.config.settings import settings
from src.workers.worker_base import BaseWorker
from src.discovery.pipeline.telemetry import Telemetry, Stage, Status, ReasonCode

try:
    import psutil
except ImportError:
    psutil = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CompanyDiscoveryWorker")

# ── Batch configurations ────────────────────────────────────────────────────
FETCH_BATCH = int(os.getenv("DISCOVERY_FETCH_BATCH", "1000"))
PROMOTION_BATCH = int(os.getenv("DISCOVERY_PROMOTION_BATCH", "250"))
QUEUE_BATCH_SIZE = int(os.getenv("QUEUE_BATCH_SIZE", "500"))
HEARTBEAT_BATCH = int(os.getenv("HEARTBEAT_BATCH", "250"))

# Sharding configuration for horizontal scaling
SHARD_ID = int(os.getenv("SHARD_ID", "0"))
NUM_SHARDS = int(os.getenv("NUM_SHARDS", "1"))

# Get Git commit hash for versioning/observability
def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"

WORKER_VERSION = "2.0.0"
GIT_COMMIT = get_git_commit()

def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        if domain.startswith("www."):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return ""

class CompanyDiscoveryWorker(BaseWorker):
    def __init__(self):
        super().__init__("CompanyDiscoveryWorker")

    def run(self):
        logger.info(f"CompanyDiscoveryWorker starting as {self.worker_id} (Version: {WORKER_VERSION}, Commit: {GIT_COMMIT})")
        logger.info(f"Sharding configuration: Shard {SHARD_ID} of {NUM_SHARDS}")
        
        while self.running:
            try:
                # 1. Parse CSV seeds (idempotent, standard bootstrap)
                self.import_csv_seeds()

                # 2. Process Candidates in batches
                self.process_candidates()

                time.sleep(settings.discovery_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in CompanyDiscoveryWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                time.sleep(60)

        self.stop()
        logger.info("CompanyDiscoveryWorker stopped.")

    def import_csv_seeds(self):
        csv_path = os.path.join(os.getcwd(), "benchmark", "companies.csv")
        if not os.path.exists(csv_path):
            return
        
        from src.api.db import get_connection, is_postgres
        conn = get_connection()
        try:
            with open(csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("company", "").strip()
                    website = row.get("website", "").strip()
                    if not name or not website:
                        continue
                    
                    domain = extract_domain(website)
                    company_id = name.lower().replace(" ", "-")

                    expected_ats = row.get("expected_ats", "").strip()
                    expected_endpoint = row.get("expected_endpoint", "").strip()
                    
                    aliases_json = None
                    if expected_ats and expected_endpoint:
                        slug = expected_endpoint.rstrip('/').split('/')[-1]
                        aliases_json = json.dumps({
                            "source": "jobhive",
                            "known_ats": expected_ats,
                            "board_url": expected_endpoint,
                            "ats_slug": slug
                        })
                    
                    # Insert company if not existing
                    if is_postgres():
                        cursor = conn.execute("SELECT aliases FROM company_identities WHERE company_id = %s", (company_id,))
                    else:
                        cursor = conn.execute("SELECT aliases FROM company_identities WHERE company_id = ?", (company_id,))
                    
                    existing = cursor.fetchone()
                    existing_aliases = existing.get("aliases") if isinstance(existing, dict) else (existing[0] if existing else None)
                    
                    if not existing:
                        if is_postgres():
                            conn.execute('''
                                INSERT INTO company_identities (company_id, domain, canonical_name, website, aliases, lifecycle_state)
                                VALUES (%s, %s, %s, %s, %s, NULL)
                                ON CONFLICT (company_id) DO NOTHING
                            ''', (company_id, domain, name, website, aliases_json))
                        else:
                            conn.execute('''
                                INSERT OR IGNORE INTO company_identities (company_id, domain, canonical_name, website, aliases, lifecycle_state)
                                VALUES (?, ?, ?, ?, ?, NULL)
                            ''', (company_id, domain, name, website, aliases_json))
                            
                        # Transition to DISCOVERED
                        from src.discovery.pipeline_state_manager import PipelineStateManager
                        PipelineStateManager.transition(company_id, "DISCOVERED", conn=conn)
                    elif existing and not existing_aliases and aliases_json:
                        if is_postgres():
                            conn.execute('UPDATE company_identities SET aliases = %s WHERE company_id = %s', (aliases_json, company_id))
                        else:
                            conn.execute('UPDATE company_identities SET aliases = ? WHERE company_id = ?', (aliases_json, company_id))
            conn.commit()
        finally:
            conn.close()

    def process_candidates(self):
        from src.api.db import get_connection, is_postgres
        from src.discovery.pipeline.fast_path_registry import FastPathRegistry

        fast_patcher = FastPathRegistry(self.db_path)
        
        # 1. Read last checkpoint ID from worker_progress
        last_id = 0
        conn = get_connection()
        try:
            if is_postgres():
                row = conn.execute("SELECT last_checkpoint FROM worker_progress WHERE worker_name = %s", (self.worker_id,)).fetchone()
            else:
                row = conn.execute("SELECT last_checkpoint FROM worker_progress WHERE worker_name = ?", (self.worker_id,)).fetchone()
            if row:
                last_id = int(row["last_checkpoint"] or 0)
        finally:
            conn.close()

        logger.info(f"Resuming discovery from checkpoint ID: {last_id}")

        processed_total = 0
        start_time = time.time()
        last_heartbeat_time = start_time
        batch_number = 0

        while self.running:
            conn = get_connection()
            try:
                # Sharded checkpoint select: fetch next 1000 items that match this shard
                if is_postgres():
                    cursor = conn.execute(
                        "SELECT id, company_id, canonical_name, domain, website, aliases "
                        "FROM company_identities "
                        "WHERE id > %s AND id %% %s = %s "
                        "ORDER BY id ASC LIMIT %s",
                        (last_id, NUM_SHARDS, SHARD_ID, FETCH_BATCH)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT id, company_id, canonical_name, domain, website, aliases "
                        "FROM company_identities "
                        "WHERE id > ? AND (id %% ? = ?) "
                        "ORDER BY id ASC LIMIT ?",
                        (last_id, NUM_SHARDS, SHARD_ID, FETCH_BATCH)
                    )
                candidates = [dict(row) for row in cursor.fetchall()]
                if not candidates:
                    logger.info("No more candidates to process. Scan cycle complete.")
                    break

                batch_number += 1
                logger.info(f"Processing candidate batch {batch_number} ({len(candidates)} rows, IDs {candidates[0]['id']} to {candidates[-1]['id']})")

                import json
                import asyncio
                from src.discovery.pipeline.sources import HeadProbeSource, StaticLandingPageSource, ExternalSearchSource, HeuristicTokenSource
                from src.discovery.pipeline.plugins.greenhouse_plugin import GreenhouseDiscoveryPlugin
                from src.discovery.pipeline.plugins.lever_plugin import LeverDiscoveryPlugin
                from src.discovery.pipeline.plugins.workday_plugin import WorkdayDiscoveryPlugin
                from src.discovery.pipeline.plugins.ashby_plugin import AshbyDiscoveryPlugin
                from src.discovery.pipeline.plugins.workable_plugin import WorkableDiscoveryPlugin
                from src.discovery.pipeline.plugins.smartrecruiters_plugin import SmartRecruitersDiscoveryPlugin
                from src.discovery.pipeline.plugins.teamtailor_plugin import TeamtailorDiscoveryPlugin
                from src.discovery.pipeline.plugins.breezy_plugin import BreezyDiscoveryPlugin
                from src.discovery.pipeline.fallback_models import DiscoveryBudget
                from src.discovery.pipeline.discovery_orchestrator import DiscoveryOrchestrator
                
                # Setup orchestrator
                sources = [HeadProbeSource(), StaticLandingPageSource(), ExternalSearchSource(), HeuristicTokenSource()]
                plugins = [
                    GreenhouseDiscoveryPlugin(), LeverDiscoveryPlugin(), WorkdayDiscoveryPlugin(), 
                    AshbyDiscoveryPlugin(), WorkableDiscoveryPlugin(), SmartRecruitersDiscoveryPlugin(), 
                    TeamtailorDiscoveryPlugin(), BreezyDiscoveryPlugin()
                ]
                orchestrator = DiscoveryOrchestrator(sources=sources, plugins=plugins)
                # Google search is often rate-limited, but we keep it enabled
                budget = DiscoveryBudget(max_http_requests=20, max_search_queries=2, max_latency_seconds=30.0)
                
                # We won't use fast_path promotion directly here anymore.
                # Instead, all candidates go to endpoint_candidates and we rely on EndpointRankingEngine.
                
                all_candidates = []
                company_ids_to_verify = []

                for cand in candidates:
                    cid = cand["company_id"]
                    try:
                        res = asyncio.run(orchestrator.execute(
                            company=cand["canonical_name"], 
                            website=cand["website"], 
                            budget=budget,
                            company_id=cid
                        ))
                        
                        plugins_results = res.get('all_candidates', [])
                        
                        for pr in plugins_results:
                            all_candidates.append({
                                "company_id": cid,
                                "provider_id": getattr(pr, 'provider_id', pr.candidate.provider_id if hasattr(pr, 'candidate') else getattr(pr, 'ats_domain', 'unknown').split('.')[0]),
                                "url": pr.url if hasattr(pr, 'url') else pr.candidate.url,
                                "discovery_source": "DiscoveryOrchestrator",
                                "evidence": [e.__dict__ for e in (pr.evidence if hasattr(pr, 'evidence') else [])],
                                "confidence_score": getattr(pr, 'confidence_score', getattr(pr, 'normalized_score', 0))
                            })
                            
                        if plugins_results:
                            company_ids_to_verify.append(cid)
                    except Exception as e:
                        logger.error(f"DiscoveryOrchestrator failed for {cid}: {e}")

                if all_candidates:
                    # Upsert into endpoint_candidates
                    cursor = conn.cursor()
                    for cand in all_candidates:
                        evidence_str = json.dumps(cand["evidence"])
                        if is_postgres():
                            cursor.execute('''
                                INSERT INTO endpoint_candidates (company_id, provider_id, url, discovery_source, evidence, confidence_score)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (company_id, provider_id, url) DO UPDATE SET
                                    confidence_score = EXCLUDED.confidence_score,
                                    times_seen = endpoint_candidates.times_seen + 1,
                                    last_seen = CURRENT_TIMESTAMP
                            ''', (cand["company_id"], cand["provider_id"], cand["url"], cand["discovery_source"], evidence_str, cand["confidence_score"]))
                        else:
                            # Fallback sqlite
                            cursor.execute('''
                                INSERT INTO endpoint_candidates (company_id, provider_id, url, discovery_source, evidence, confidence_score)
                                VALUES (?, ?, ?, ?, ?, ?)
                                ON CONFLICT (company_id, provider_id, url) DO UPDATE SET
                                    confidence_score = excluded.confidence_score,
                                    times_seen = endpoint_candidates.times_seen + 1,
                                    last_seen = CURRENT_TIMESTAMP
                            ''', (cand["company_id"], cand["provider_id"], cand["url"], cand["discovery_source"], evidence_str, cand["confidence_score"]))
                    
                    # Transition all to VERIFICATION_PENDING (this creates the queue payload)
                    if company_ids_to_verify:
                        from src.discovery.pipeline_state_manager import PipelineStateManager
                        PipelineStateManager.transition_batch(
                            company_ids_to_verify, 
                            "VERIFICATION_PENDING", 
                            queue_op_name="verification_queue",
                            conn=conn
                        )
                    logger.info(f"Enqueued {len(company_ids_to_verify)} companies for verification.")

                conn.commit()

                # Update state progress
                processed_total += len(candidates)
                last_id = candidates[-1]["id"]

                # Robust heartbeats & metrics logging
                now = time.time()
                if processed_total % HEARTBEAT_BATCH == 0 or (now - last_heartbeat_time) >= 30:
                    self.report_progress(last_id, processed_total, start_time, batch_number)
                    last_heartbeat_time = now

            finally:
                conn.close()

    def report_progress(self, last_id: int, processed_total: int, start_time: float, batch_number: int):
        from src.api.db import get_connection, is_postgres
        now = time.time()
        elapsed = now - start_time
        rate = round(processed_total / (elapsed / 60.0), 1) if elapsed > 0 else 0.0
        
        # Calculate overall ETA (based on 57k total companies)
        TOTAL_COMPANIES = 57422
        remaining = TOTAL_COMPANIES - processed_total
        eta_seconds = (remaining / (processed_total / elapsed)) if processed_total > 0 else 0.0
        eta_str = f"{int(eta_seconds // 3600)}h {int((eta_seconds % 3600) // 60)}m"

        # System Metrics
        cpu_usage = 0.0
        memory_usage = 0.0
        if psutil:
            try:
                process = psutil.Process(os.getpid())
                memory_usage = round(process.memory_info().rss / (1024 * 1024), 2)
                cpu_usage = round(psutil.cpu_percent(), 2)
            except Exception:
                pass

        logger.info(
            f"Progress: {processed_total} / {TOTAL_COMPANIES} companies processed | "
            f"Rate: {rate} companies/min | CPU: {cpu_usage}% | RAM: {memory_usage}MB | "
            f"ETA: {eta_str}"
        )

        conn = get_connection()
        try:
            # Write to worker_progress (UPSERT)
            if is_postgres():
                conn.execute("""
                    INSERT INTO worker_progress (
                        worker_name, status, last_checkpoint, batch_number, processed, 
                        success_count, failure_count, retry_count, companies_per_min, eta,
                        memory_usage, cpu_usage, worker_version, git_commit, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (worker_name) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_checkpoint = EXCLUDED.last_checkpoint,
                        batch_number = EXCLUDED.batch_number,
                        processed = EXCLUDED.processed,
                        companies_per_min = EXCLUDED.companies_per_min,
                        eta = EXCLUDED.eta,
                        memory_usage = EXCLUDED.memory_usage,
                        cpu_usage = EXCLUDED.cpu_usage,
                        git_commit = EXCLUDED.git_commit,
                        updated_at = EXCLUDED.updated_at
                """, (
                    self.worker_id, "RUNNING", str(last_id), batch_number, processed_total,
                    processed_total, 0, 0, rate, eta_str,
                    memory_usage, cpu_usage, WORKER_VERSION, GIT_COMMIT, now
                ))

                # Log to worker_metrics history table
                conn.execute("""
                    INSERT INTO worker_metrics (timestamp, worker, processed, rate, cpu, memory, eta)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (now, self.worker_id, processed_total, rate, cpu_usage, memory_usage, eta_seconds))
            else:
                conn.execute("""
                    INSERT INTO worker_progress (
                        worker_name, status, last_checkpoint, batch_number, processed, 
                        success_count, failure_count, retry_count, companies_per_min, eta,
                        memory_usage, cpu_usage, worker_version, git_commit, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (worker_name) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_checkpoint = EXCLUDED.last_checkpoint,
                        batch_number = EXCLUDED.batch_number,
                        processed = EXCLUDED.processed,
                        companies_per_min = EXCLUDED.companies_per_min,
                        eta = EXCLUDED.eta,
                        memory_usage = EXCLUDED.memory_usage,
                        cpu_usage = EXCLUDED.cpu_usage,
                        git_commit = EXCLUDED.git_commit,
                        updated_at = EXCLUDED.updated_at
                """, (
                    self.worker_id, "RUNNING", str(last_id), batch_number, processed_total,
                    processed_total, 0, 0, rate, eta_str,
                    memory_usage, cpu_usage, WORKER_VERSION, GIT_COMMIT, now
                ))

                conn.execute("""
                    INSERT INTO worker_metrics (timestamp, worker, processed, rate, cpu, memory, eta)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (now, self.worker_id, processed_total, rate, cpu_usage, memory_usage, eta_seconds))
            conn.commit()
        except Exception as ex:
            logger.error(f"Failed to record progress to database: {ex}")
        finally:
            conn.close()

        # Call BaseWorker heartbeat
        self.heartbeat(jobs_processed=processed_total)

if __name__ == "__main__":
    worker = CompanyDiscoveryWorker()
    worker.run()
