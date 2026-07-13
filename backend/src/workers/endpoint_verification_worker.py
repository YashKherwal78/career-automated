import os
import sys
import time
import logging
import asyncio
from urllib.parse import urlparse
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

def _extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url if url.startswith('http') else f"https://{url}")
        host = parsed.netloc or parsed.path
        if host.startswith('www.'):
            host = host[4:]
        return host.lower().strip().split(':')[0]
    except Exception:
        return ""


def _normalize_company_id(domain: str, company_name: str = "") -> str:
    if domain:
        return domain
    return company_name.lower().replace(' ', '-').strip() or f"unknown-{int(time.time())}"


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

    def _ensure_company_identity(self, domain: str, website: str, canonical_name: str) -> str:
        """Ensure a minimal company identity exists for verification payloads."""
        company_id = _normalize_company_id(domain, canonical_name)
        from src.api.db import get_connection, is_postgres
        conn = get_connection()
        try:
            if is_postgres():
                row = conn.execute(
                    "SELECT company_id FROM company_identities WHERE company_id = %s OR domain = %s OR canonical_name = %s",
                    (company_id, domain, canonical_name)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT company_id FROM company_identities WHERE company_id = ? OR domain = ? OR canonical_name = ?",
                    (company_id, domain, canonical_name)
                ).fetchone()
            if row:
                return row["company_id"]
            if is_postgres():
                conn.execute(
                    "INSERT INTO company_identities (company_id, domain, canonical_name, website) VALUES (%s, %s, %s, %s) ON CONFLICT (company_id) DO NOTHING",
                    (company_id, domain, canonical_name or company_id, website or domain)
                )
            else:
                conn.execute(
                    "INSERT OR IGNORE INTO company_identities (company_id, domain, canonical_name, website) VALUES (?, ?, ?, ?)",
                    (company_id, domain, canonical_name or company_id, website or domain)
                )
            conn.commit()
        finally:
            conn.close()
        return company_id

    async def run_async(self):
        logger.info(f"EndpointVerificationWorker starting as {self.worker_id}")
        while self.running:
            try:
                company_id = None
                
# 1. Try popping from verification_queue first
                current_queue = None
                q_item = self.queue.pop("verification_queue")
                if q_item:
                    payload = q_item["payload"]
                    company_id = payload.get("company_id")
                    item_id = q_item["_item_id"]
                    current_queue = q_item.get("queue_name", "verification_queue")
                    logger.info(f"Popped company from verification queue: {company_id or payload.get('domain') or payload.get('website')} - queue={current_queue}")

                    if not company_id:
                        # Resolve by payload domain/website/name and optionally create a company identity.
                        domain = payload.get("domain") or _extract_domain(payload.get("website", ""))
                        website = payload.get("website")
                        canonical_name = payload.get("company_name")
                        company_id = self._ensure_company_identity(domain, website, canonical_name)

                # 1b. Fallback: Try discovery_queue if verification queue is empty or payload was not resolvable
                if not company_id:
                    q_item = self.queue.pop("discovery_queue")
                    if q_item:
                        payload = q_item["payload"]
                        company_id = payload.get("company_id")
                        item_id = q_item["_item_id"]
                        current_queue = q_item.get("queue_name", "discovery_queue")
                        logger.info(f"Popped company from discovery queue: {company_id or payload.get('domain') or payload.get('website')} - queue={current_queue}")

                        if not company_id:
                            domain = payload.get("domain") or _extract_domain(payload.get("website", ""))
                            website = payload.get("website")
                            canonical_name = payload.get("company_name")
                            company_id = self._ensure_company_identity(domain, website, canonical_name)
                
                # 2. Fallback: Select a company without an ACTIVE endpoint
                if not company_id:
                    from src.api.db import get_connection
                    conn = get_connection()
                    try:
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
                    finally:
                        conn.close()

                if not company_id:
                    # No companies to verify
                    self.heartbeat()
                    await asyncio.sleep(settings.crawler_poll_interval)
                    continue

                # Load company details
                company_info = None
                from src.api.db import get_connection, is_postgres
                conn = get_connection()
                try:
                    if is_postgres():
                        cursor = conn.execute("SELECT canonical_name, website, domain FROM company_identities WHERE company_id = %s", (company_id,))
                    else:
                        cursor = conn.execute("SELECT canonical_name, website, domain FROM company_identities WHERE company_id = ?", (company_id,))
                    row = cursor.fetchone()
                    if row:
                        company_info = dict(row)
                finally:
                    conn.close()

                if not company_info:
                    logger.warning(f"Company ID {company_id} not found in identities.")
                    if q_item:
                        self.queue.ack(current_queue, item_id)
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
                    def endpoint_url(endpoint):
                        if isinstance(endpoint, dict):
                            return endpoint.get("url")
                        return getattr(endpoint, "url", None)

                    res = await self.orchestrator.execute(company_id, website, budget, run_id=run_id, company_id=company_id)
                    verified = res.get("verified", [])

                    if verified:
                        logger.info(f"Successfully verified ATS endpoint for {company_id}!")

                        # Update state machine: VERIFIED
                        from src.discovery.pipeline_state_manager import PipelineStateManager
                        PipelineStateManager.transition(company_id, "VERIFIED")

                        endpoint_urls = []
                        for v in verified:
                            if isinstance(v, dict):
                                url = v.get("endpoint") or v.get("canonical_endpoint") or v.get("url")
                            else:
                                url = getattr(v, "url", None) or getattr(v, "endpoint", None)
                            if url:
                                endpoint_urls.append(url)

                        # Push to crawl_queue for JobCrawlerWorker
                        self.queue.push("crawl_queue", {"company_id": company_id})
                        
                        # Emit event
                        self.metrics.record_event("EndpointVerified", {
                            "company_id": company_id,
                            "endpoints": endpoint_urls,
                            "worker_id": self.worker_id,
                            "source_queue": current_queue
                        })
                        self.metrics.update_business_metric("total_verified_endpoints", 1)
                        
                        Telemetry.record_event(
                            stage=Stage.VERIFICATION_EXECUTED,
                            status=Status.SUCCESS,
                            run_id=run_id,
                            company_id=company_id,
                            worker_name=self.worker_id,
                            metadata={"queue": current_queue, "endpoints": endpoint_urls}
                        )
                        self.heartbeat(jobs_processed=1)
                        Telemetry.finish_run(run_id, Status.SUCCESS)
                    else:
                        logger.info(f"Verification failed for {company_id}")

                        # Update state machine: VERIFICATION_FAILED
                        from src.discovery.pipeline_state_manager import PipelineStateManager
                        PipelineStateManager.transition(company_id, "VERIFICATION_FAILED", failure_reason="NO_VALID_ATS_ENDPOINTS")

                        self.metrics.record_event("EndpointFailed", {
                            "company_id": company_id,
                            "reason": "No valid ATS endpoints discovered",
                            "worker_id": self.worker_id,
                            "source_queue": current_queue
                        })
                        Telemetry.record_event(
                            stage=Stage.VERIFICATION_EXECUTED,
                            status=Status.FAILURE,
                            run_id=run_id,
                            company_id=company_id,
                            worker_name=self.worker_id,
                            reason_code=ReasonCode.UNKNOWN_ATS,
                            metadata={"queue": current_queue, "reason": "No valid ATS endpoints discovered"}
                        )
                        self.heartbeat(failure_increment=1)
                        Telemetry.finish_run(run_id, Status.SUCCESS)
                except Exception as ex:
                    # Update state machine: VERIFICATION_FAILED
                    from src.discovery.pipeline_state_manager import PipelineStateManager
                    PipelineStateManager.transition(company_id, "VERIFICATION_FAILED", failure_reason="VERIFICATION_EXCEPTION")

                    Telemetry.record_event(
                        stage=Stage.VERIFICATION_EXECUTED,
                        status=Status.FAILURE,
                        run_id=run_id,
                        company_id=company_id,
                        worker_name=self.worker_id,
                        reason_code=ReasonCode.NETWORK_TIMEOUT,
                        metadata={"queue": current_queue, "error": str(ex)}
                    )
                    Telemetry.finish_run(run_id, Status.FAILURE)
                    raise ex

                if q_item:
                    self.queue.ack(current_queue, item_id)

                await asyncio.sleep(5)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in EndpointVerificationWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                if q_item and item_id:
                    self.queue.nack(current_queue or "verification_queue", item_id, reason=str(e), backoff_seconds=300)
                await asyncio.sleep(30)

        self.stop()
        logger.info("EndpointVerificationWorker stopped.")

if __name__ == "__main__":
    worker = EndpointVerificationWorker()
    asyncio.run(worker.run_async())
