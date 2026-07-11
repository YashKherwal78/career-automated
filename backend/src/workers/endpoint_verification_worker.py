import os
import sys
import time
import sqlite3
import logging
import asyncio
from src.config.settings import settings
from src.workers.worker_base import BaseWorker
from src.discovery.pipeline.discovery_orchestrator import DiscoveryOrchestrator
from src.discovery.pipeline.sources import HeadProbeSource, StaticLandingPageSource, ExternalSearchSource
from src.discovery.pipeline.plugins.greenhouse_plugin import GreenhouseDiscoveryPlugin
from src.discovery.pipeline.plugins.lever_plugin import LeverDiscoveryPlugin
from src.discovery.pipeline.plugins.workday_plugin import WorkdayDiscoveryPlugin
from src.discovery.pipeline.plugins.ashby_plugin import AshbyDiscoveryPlugin
from src.discovery.pipeline.plugins.workable_plugin import WorkableDiscoveryPlugin
from src.discovery.pipeline.plugins.smartrecruiters_plugin import SmartRecruitersDiscoveryPlugin
from src.discovery.pipeline.plugins.teamtailor_plugin import TeamtailorDiscoveryPlugin
from src.discovery.pipeline.plugins.breezy_plugin import BreezyDiscoveryPlugin
from src.discovery.pipeline.plugins.recruitee_plugin import RecruiteeDiscoveryPlugin
from src.discovery.pipeline.plugins.jobvite_plugin import JobviteDiscoveryPlugin
from src.discovery.pipeline.caches import ReplayCache
from src.discovery.pipeline.fallback_models import DiscoveryBudget

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EndpointVerificationWorker")

class EndpointVerificationWorker(BaseWorker):
    def __init__(self):
        super().__init__("EndpointVerificationWorker")
        sources = [HeadProbeSource(), StaticLandingPageSource(), ExternalSearchSource()]
        
        plugins = [
            GreenhouseDiscoveryPlugin(),
            LeverDiscoveryPlugin(),
            WorkdayDiscoveryPlugin()
        ]
        
        if settings.enable_discovery_plugin_ashby:
            plugins.append(AshbyDiscoveryPlugin())
        if settings.enable_discovery_plugin_workable:
            plugins.append(WorkableDiscoveryPlugin())
        if settings.enable_discovery_plugin_smartrecruiters:
            plugins.append(SmartRecruitersDiscoveryPlugin())
        if settings.enable_discovery_plugin_teamtailor:
            plugins.append(TeamtailorDiscoveryPlugin())
        if settings.enable_discovery_plugin_breezy:
            plugins.append(BreezyDiscoveryPlugin())
        if settings.enable_discovery_plugin_recruitee:
            plugins.append(RecruiteeDiscoveryPlugin())
        if settings.enable_discovery_plugin_jobvite:
            plugins.append(JobviteDiscoveryPlugin())
            
        replay_cache = ReplayCache(self.db_path)
        self.orchestrator = DiscoveryOrchestrator(
            sources=sources,
            plugins=plugins,
            replay_cache=replay_cache
        )

    async def run_async(self):
        logger.info(f"EndpointVerificationWorker starting as {self.worker_id}")
        while self.running:
            try:
                company_id = None
                
                # 1. Try popping from discovery_queue
                q_item = self.queue.pop("discovery_queue")
                if q_item:
                    company_id = q_item["payload"].get("company_id")
                    item_id = q_item["_item_id"]
                    logger.info(f"Popped company from queue: {company_id}")
                
                # 2. Fallback: Select a company without an ACTIVE endpoint
                if not company_id:
                    with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                        conn.row_factory = sqlite3.Row
                        cursor = conn.execute('''
                            SELECT i.company_id 
                            FROM company_identities i
                            LEFT JOIN ats_registry r ON i.company_id = r.company_id AND r.status = 'ACTIVE'
                            WHERE r.company_id IS NULL
                            LIMIT 1
                        ''')
                        row = cursor.fetchone()
                        if row:
                            company_id = row["company_id"]
                            logger.info(f"Polled company from DB: {company_id}")

                if not company_id:
                    # No companies to verify
                    self.heartbeat()
                    await asyncio.sleep(settings.crawler_poll_interval)
                    continue

                # Load company details
                company_info = None
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("SELECT canonical_name, website, domain FROM company_identities WHERE company_id = ?", (company_id,))
                    row = cursor.fetchone()
                    if row:
                        company_info = dict(row)

                if not company_info:
                    logger.warning(f"Company ID {company_id} not found in identities.")
                    if q_item:
                        self.queue.ack("discovery_queue", item_id)
                    continue

                website = company_info.get("website") or company_info.get("domain")
                if not website:
                    logger.warning(f"No website or domain for company {company_id}")
                    if q_item:
                        self.queue.ack("discovery_queue", item_id)
                    continue

                if not website.startswith("http"):
                    website = f"https://{website}"

                # Budget parameters
                budget = DiscoveryBudget(max_http_requests=25, max_latency_seconds=30.0, max_search_queries=5)
                
                run_id = f"verification-run-{company_id}-{int(time.time())}"
                from src.discovery.pipeline.telemetry import Telemetry, Stage, Status, ReasonCode
                Telemetry.start_run(run_id, "EndpointVerificationWorker", trigger="Cron")
                
                logger.info(f"Running verification for: {company_info['canonical_name']} ({website})")
                try:
                    res = await self.orchestrator.execute(company_id, website, budget, run_id=run_id, company_id=company_id)
                    verified = res.get("verified", [])

                    if verified:
                        logger.info(f"Successfully verified ATS endpoint for {company_id}!")
                        # Push to crawl_queue for JobCrawlerWorker
                        self.queue.push("crawl_queue", {"company_id": company_id})
                        
                        # Emit event
                        self.metrics.record_event("EndpointVerified", {
                            "company_id": company_id,
                            "endpoints": [v.url for v in verified],  # Candidate objects, not dicts
                            "worker_id": self.worker_id
                        })
                        self.metrics.update_business_metric("total_verified_endpoints", 1)
                        
                        self.heartbeat(jobs_processed=1)
                        Telemetry.finish_run(run_id, Status.SUCCESS)
                    else:
                        logger.info(f"Verification failed for {company_id}")
                        self.metrics.record_event("EndpointFailed", {
                            "company_id": company_id,
                            "reason": "No valid ATS endpoints discovered",
                            "worker_id": self.worker_id
                        })
                        self.heartbeat(failure_increment=1)
                        Telemetry.finish_run(run_id, Status.SUCCESS)
                except Exception as ex:
                    Telemetry.finish_run(run_id, Status.FAILURE)
                    raise ex

                if q_item:
                    self.queue.ack("discovery_queue", item_id)

                await asyncio.sleep(5)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in EndpointVerificationWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                if q_item:
                    self.queue.nack("discovery_queue", item_id, reason=str(e))
                await asyncio.sleep(30)

        self.stop()
        logger.info("EndpointVerificationWorker stopped.")

if __name__ == "__main__":
    worker = EndpointVerificationWorker()
    asyncio.run(worker.run_async())
