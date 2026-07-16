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
                
                inserted = self.repos.discovery.import_csv_seed(company_id, domain, name, website, aliases_json)
                
                if inserted:
                    # Transition to DISCOVERED
                    from src.discovery.pipeline_state_manager import PipelineStateManager
                    with self.repos.transaction() as conn:
                        PipelineStateManager.transition(company_id, "DISCOVERED", conn=conn)

    def process_candidates(self):
        fast_patcher = FastPathRegistry(self.db_path)
        
        # 1. Read last checkpoint ID from worker_progress
        last_id = self.repos.discovery.get_checkpoint(self.worker_id)

        logger.info(f"Resuming discovery from checkpoint ID: {last_id}")

        processed_total = 0
        start_time = time.time()
        last_heartbeat_time = start_time
        batch_number = 0

        while self.running:
            try:
                # Sharded checkpoint select: fetch next 1000 items that match this shard
                candidates = self.repos.discovery.next_batch(last_id, NUM_SHARDS, SHARD_ID, FETCH_BATCH)
                
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
                    self.repos.discovery.save_candidates(all_candidates)
                    
                    # Transition all to VERIFICATION_PENDING (this creates the queue payload)
                    if company_ids_to_verify:
                        self.repos.discovery.enqueue_for_verification(company_ids_to_verify)
                        
                    logger.info(f"Enqueued {len(company_ids_to_verify)} companies for verification.")

                # Update state progress
                processed_total += len(candidates)
                last_id = candidates[-1]["id"]

                # Robust heartbeats & metrics logging
                now = time.time()
                if processed_total % HEARTBEAT_BATCH == 0 or (now - last_heartbeat_time) >= 30:
                    self.report_progress(last_id, processed_total, start_time, batch_number)
                    last_heartbeat_time = now

            except Exception as loop_ex:
                logger.error(f"Error during candidate processing: {loop_ex}")

    def report_progress(self, last_id: int, processed_total: int, start_time: float, batch_number: int):
        self.repos.metrics.update_worker_progress(
            self.worker_id, last_id, batch_number, processed_total, start_time, WORKER_VERSION, GIT_COMMIT
        )

        # Call BaseWorker heartbeat
        self.heartbeat(jobs_processed=processed_total)

if __name__ == "__main__":
    worker = CompanyDiscoveryWorker()
    worker.run()
