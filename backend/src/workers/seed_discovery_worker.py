import os
import sys
import time
import json
import logging
import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
from src.workers.worker_base import BaseWorker
from src.discovery.pipeline.telemetry import Telemetry, Stage, Status
from src.discovery.seed_sources.yc_source import YCombinatorSource
from src.discovery.seed_sources.search_source import SearchSource

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SeedDiscoveryWorker")

class SeedDiscoveryWorker(BaseWorker):
    def __init__(self):
        super().__init__("SeedDiscoveryWorker")
        self.sources = [
            YCombinatorSource(),
            SearchSource()
        ]
        self.interval = 3600  # Poll every hour
        
        pass
        
    def _normalize_domain(self, website: str) -> str:
        if not website:
            return ""
        parsed = urlparse(website.lower() if website.startswith("http") else f"https://{website.lower()}")
        domain = parsed.netloc or parsed.path
        domain = domain.replace("www.", "").strip("/")
        return domain

    def _company_exists(self, domain: str) -> bool:
        return self.repos.discovery.company_exists(domain)

    def _persist_seed_metadata(self, seed: dict, now: float):
        domain = self._normalize_domain(seed["website"])
        company_id = seed.get("company_id") or domain.split(".")[0]
        dt_str = datetime.fromtimestamp(now, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        self.repos.discovery.persist_seed_metadata(company_id, seed, domain, dt_str)

    async def run_async(self):
        logger.info("SeedDiscoveryWorker started.")
        
        while self.running:
            try:
                now = time.time()
                logger.info("Starting automated company seed discovery cycle...")
                
                total_discovered = 0
                unique_discovered = 0
                
                for source in self.sources:
                    if not source.enabled:
                        continue
                        
                    logger.info(f"Running seed source: {source.name}")
                    try:
                        seeds = await source.discover()
                        total_discovered += len(seeds)
                        
                        for seed in seeds:
                            domain = self._normalize_domain(seed["website"])
                            if not domain:
                                continue
                                
                            if not self._company_exists(domain):
                                unique_discovered += 1
                                self._persist_seed_metadata(seed, now)
                                
                                # Enqueue directly to discovery_queue to verify it immediately!
                                payload_company_id = seed.get("company_id") or domain.split(".")[0]
                                self.queue.push("verification_queue", {
                                    "company_id": payload_company_id,
                                    "canonical_name": seed["name"],
                                    "website": seed["website"]
                                })
                                Telemetry.record_event(
                                    stage=Stage.VERIFICATION_QUEUED,
                                    status=Status.SUCCESS,
                                    run_id=f"seed-verification-{payload_company_id}-{int(time.time())}",
                                    company_id=payload_company_id,
                                    worker_name=self.worker_id,
                                    metadata={"source": "SeedDiscoveryWorker"}
                                )
                                logger.info(f"Discovered new unique company seed: {seed['name']} ({seed['website']}) enqueued.")
                    except Exception as e:
                        logger.error(f"Error in seed source {source.name}: {e}")
                        
                logger.info(f"Discovery cycle complete. Total Discovered: {total_discovered}, Unique Seeds Enqueued: {unique_discovered}")
                
                # Emit telemetry events
                self.metrics.record_event("SeedsDiscovered", {
                    "total": total_discovered,
                    "unique": unique_discovered,
                    "worker_id": self.worker_id
                })
                self.heartbeat(jobs_processed=unique_discovered)
                
                # Sleep until next cycle
                await asyncio.sleep(self.interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in SeedDiscoveryWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                await asyncio.sleep(30)
                
        self.stop()
        logger.info("SeedDiscoveryWorker stopped.")

if __name__ == "__main__":
    worker = SeedDiscoveryWorker()
    asyncio.run(worker.run_async())
