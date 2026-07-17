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
            WorkdayDiscoveryPlugin(),
            AshbyDiscoveryPlugin(),
        ]
        
        replay_cache = ReplayCache(settings.db_path)
        self.orchestrator = DiscoveryOrchestrator(
            sources=sources,
            plugins=plugins,
            replay_cache=replay_cache
        )

    def _ensure_company_identity(self, domain: str, website: str, canonical_name: str) -> str:
        """Ensure a minimal company identity exists for verification payloads."""
        company_id = _normalize_company_id(domain, canonical_name)
        return self.repos.company.ensure_company_identity(company_id, domain, canonical_name, website)

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
                    company_id = self.repos.company.get_company_without_active_endpoint()
                    if company_id:
                        logger.info(f"Polled company from DB: {company_id}")

                if not company_id:
                    # No companies to verify
                    self.heartbeat()
                    await asyncio.sleep(settings.crawler_poll_interval)
                    continue
                    
                # Transition to VERIFYING state if not polling fallback
                if q_item:
                    from src.discovery.pipeline_state_manager import PipelineStateManager
                    try:
                        PipelineStateManager.transition(company_id, "VERIFYING")
                    except Exception as e:
                        logger.warning(f"Could not transition {company_id} to VERIFYING (maybe state mismatch): {e}")

                # Load company details
                company_info = self.repos.company.get_company_info(company_id)

                if not company_info:
                    logger.warning(f"Company ID {company_id} not found in identities.")
                    if q_item:
                        self.queue.ack(current_queue, item_id)
                    continue

                if company_info.get("verification_source") == "IMPORTED_REGISTRY":
                    logger.info(f"Skipping verification for {company_id} (IMPORTED_REGISTRY source).")
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

                # New V3 Verification Logic
                from src.discovery.endpoint_ranking_engine import EndpointRankingEngine
                from src.discovery.endpoint_intelligence_service import EndpointIntelligenceService
                from src.discovery.ats_detector import DetectorRegistry
                from src.discovery.pipeline.telemetry import Telemetry, Stage, Status, ReasonCode
                import httpx
                
                logger.info(f"Running verification for: {company_info['canonical_name']} ({website})")
                
                try:
                    candidates = EndpointRankingEngine.get_ranked_candidates(company_id)
                    verified_providers = set()
                    
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                        for cand in candidates:
                            # Skip if we already verified an endpoint for this specific ATS
                            if cand.provider_id in verified_providers:
                                logger.info(f"Skipping candidate for {cand.provider_id} since we already verified one.")
                                continue
                                
                            try:
                                resp = await client.get(cand.url)
                                detector = DetectorRegistry.detect_all(cand.url, resp)
                                
                                if detector and detector.provider_id == cand.provider_id:
                                    logger.info(f"Verified ATS {detector.provider_id} at {cand.url}")
                                    EndpointIntelligenceService.report_verification_success(company_id, cand.provider_id, cand.url)
                                    
                                    # Insert canonical to ats_registry
                                    canonical_url = detector.extract_canonical_url(cand.url, resp)
                                    self.repos.company.report_canonical_endpoint(
                                        company_id=company_id,
                                        provider_id=cand.provider_id,
                                        candidate_id=cand.candidate_id,
                                        endpoint=cand.url,
                                        canonical_endpoint=canonical_url
                                    )
                                    
                                    with self.repos.transaction() as db_conn:
                                        EndpointIntelligenceService.log_registry_change(db_conn, company_id, cand.provider_id, None, canonical_url, "INITIAL_DISCOVERY")
                                    
                                    verified_providers.add(cand.provider_id)
                                else:
                                    # Verification failed (e.g. valid URL but no ATS signature matched)
                                    reason = "SignatureMismatch" if resp.status_code == 200 else f"HTTP_{resp.status_code}"
                                    EndpointIntelligenceService.report_verification_failure(company_id, cand.provider_id, cand.url, reason)
                                    
                            except Exception as http_e:
                                logger.warning(f"Failed to fetch {cand.url}: {http_e}")
                                EndpointIntelligenceService.report_verification_failure(company_id, cand.provider_id, cand.url, type(http_e).__name__)

                    if verified_providers:
                        from src.discovery.pipeline_state_manager import PipelineStateManager
                        PipelineStateManager.transition(
                            company_id, 
                            "VERIFIED", 
                            queue_op={"queue_name": "crawl_queue", "payload": {"company_id": company_id}}
                        )
                        self.metrics.record_event("EndpointVerified", {
                            "company_id": company_id,
                            "endpoints": list(verified_providers),
                            "worker_id": self.worker_id,
                            "source_queue": current_queue
                        })
                        self.metrics.update_business_metric("total_verified_endpoints", 1)
                        
                        Telemetry.record_event(
                            stage=Stage.VERIFICATION_EXECUTED,
                            status=Status.SUCCESS,
                            run_id="V3_VERIFICATION",
                            company_id=company_id,
                            worker_name=self.worker_id,
                            metadata={"queue": current_queue, "endpoints": list(verified_providers)}
                        )
                        self.heartbeat(jobs_processed=1)
                        Telemetry.finish_run("V3_VERIFICATION", Status.SUCCESS)
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
                            run_id="V3_VERIFICATION",
                            company_id=company_id,
                            worker_name=self.worker_id,
                            reason_code=ReasonCode.UNKNOWN_ATS,
                            metadata={"queue": current_queue, "reason": "No valid ATS endpoints discovered"}
                        )
                        self.heartbeat(failure_increment=1)
                        Telemetry.finish_run("V3_VERIFICATION", Status.SUCCESS)
                except Exception as ex:
                    import traceback
                    logger.error(f"ORIGINAL VERIFICATION ERROR: {ex}")
                    traceback.print_exc()
                    
                    # Update state machine: VERIFICATION_FAILED
                    from src.discovery.pipeline_state_manager import PipelineStateManager
                    PipelineStateManager.transition(company_id, "VERIFICATION_FAILED", failure_reason="VERIFICATION_EXCEPTION")

                    Telemetry.record_event(
                        stage=Stage.VERIFICATION_EXECUTED,
                        status=Status.FAILURE,
                        run_id="V3_VERIFICATION",
                        company_id=company_id,
                        worker_name=self.worker_id,
                        reason_code=ReasonCode.NETWORK_TIMEOUT,
                        metadata={"queue": current_queue, "error": str(ex)}
                    )
                    Telemetry.finish_run("V3_VERIFICATION", Status.FAILURE)
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
