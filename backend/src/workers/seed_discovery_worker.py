import os
import sys
import time
import json
import logging
import sqlite3
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
        if not domain:
            return True
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            cursor = conn.execute("SELECT 1 FROM company_identities WHERE domain = ? OR company_id = ?", (domain, domain.split(".")[0]))
            return cursor.fetchone() is not None

    def _persist_seed_metadata(self, seed: dict, now: float):
        domain = self._normalize_domain(seed["website"])
        company_id = seed.get("company_id") or domain.split(".")[0]
        
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # 1. Insert seed to company_identities
            conn.execute(
                """
                INSERT OR IGNORE INTO company_identities (company_id, legal_name, canonical_name, website, domain)
                VALUES (?, ?, ?, ?, ?)
                """,
                (company_id, seed["name"], company_id, seed["website"], domain)
            )
            
            # 2. Insert metadata to company_discovery_sources
            dt_str = datetime.fromtimestamp(now, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor = conn.execute(
                "SELECT first_seen FROM company_discovery_sources WHERE company_name = ? AND source = ? AND discovery_type = ?",
                (seed["name"], seed["source"], "automated")
            )
            row = cursor.fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE company_discovery_sources
                    SET last_seen = ?, confidence = ?
                    WHERE company_name = ? AND source = ? AND discovery_type = ?
                    """,
                    (dt_str, int(seed.get("confidence", 1.0) * 10), seed["name"], seed["source"], "automated")
                )
            else:
                conn.execute(
                    """
                    INSERT INTO company_discovery_sources (company_name, source, discovery_type, confidence, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (seed["name"], seed["source"], "automated", int(seed.get("confidence", 1.0) * 10), dt_str, dt_str)
                )
            conn.commit()

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
