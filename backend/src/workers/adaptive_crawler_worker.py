import os
import sys
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional

from src.workers.worker_base import BaseWorker
from src.config.settings import settings
from src.discovery.models import Board, StandardBoardIdentity
from src.discovery.pipeline.sync_session import BoardSyncSession
from src.discovery.pipeline.adaptive_provider_config import adaptive_manager, PROVIDER_CLASS_MAPPING

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AdaptiveCrawlerWorker")

class AdaptiveCrawlerWorker(BaseWorker):
    def __init__(self):
        super().__init__("AdaptiveCrawlerWorker")
        from src.discovery.connectors.bootstrap import bootstrap_connectors
        bootstrap_connectors()
        self.stats_metrics = {
            "companies_crawled": 0,
            "jobs_extracted": 0,
            "start_time": time.time(),
        }

    def run(self):
        logger.info(f"AdaptiveCrawlerWorker starting worker_id={self.worker_id}")
        asyncio.run(self.run_async())

    async def run_async(self):
        while self.running:
            try:
                providers = list(PROVIDER_CLASS_MAPPING.keys())
                tasks = []
                for provider_id in providers:
                    cfg = adaptive_manager.get_config(provider_id)
                    if time.time() < cfg.pause_until:
                        continue  # Skip paused provider
                    tasks.append(self._crawl_provider_batch(provider_id, cfg.current_workers))

                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)

                self.heartbeat()
                elapsed_min = max(0.1, (time.time() - self.stats_metrics["start_time"]) / 60.0)
                co_pm = self.stats_metrics["companies_crawled"] / elapsed_min
                jobs_pm = self.stats_metrics["jobs_extracted"] / elapsed_min
                logger.info(f"Adaptive Throughput: {co_pm:.1f} companies/min, {jobs_pm:.1f} jobs/min (Total Co: {self.stats_metrics['companies_crawled']}, Total Jobs: {self.stats_metrics['jobs_extracted']})")
                await asyncio.sleep(5)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"AdaptiveCrawlerWorker cycle error: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def _crawl_provider_batch(self, provider_id: str, batch_size: int):
        semaphore = asyncio.Semaphore(batch_size)

        async def _crawl_single():
            async with semaphore:
                reserved = self.repos.company_state.reserve_due_board(self.worker_id, provider_id=provider_id, lock_duration=300)
                if not reserved:
                    return

                board_id = reserved["id"]
                company_id = reserved.get("company_id") or reserved.get("company_domain")
                endpoint = reserved.get("endpoint") or f"https://{company_id}"

                if provider_id == "workday":
                    from src.discovery.pipeline.parsers import WorkdayParser
                    from src.discovery.models import WorkdayBoardIdentity
                    identity_from_parser, _, _ = WorkdayParser().parse(endpoint)
                    if identity_from_parser and isinstance(identity_from_parser, WorkdayBoardIdentity):
                        identity = identity_from_parser
                    else:
                        identity = WorkdayBoardIdentity(ats="workday", tenant="unknown", site="unknown")

                else:
                    identity = StandardBoardIdentity(ats=provider_id, board_token=str(company_id))

                board = Board(
                    company_id=str(company_id),
                    identity=identity,
                    endpoint=endpoint,
                    provider=provider_id,
                    discovered_by="AdaptiveCrawlerWorker",
                    discovered_at=time.time(),
                    last_verified_at=time.time(),
                    metadata={"company_id": company_id, "board_id": board_id}
                )

                session = BoardSyncSession(board, db_path=self.db_path)
                t0 = time.time()
                stats = await session.execute()
                latency_ms = (time.time() - t0) * 1000.0

                success = stats.get("success", False)
                err_msg = str(stats.get("error_message") or "").lower()
                is_429 = "429" in err_msg or "rate limit" in err_msg
                is_403 = "403" in err_msg or "waf" in err_msg or "challenge" in err_msg

                adaptive_manager.update_telemetry(provider_id, success=success, latency_ms=latency_ms, is_429=is_429, is_403=is_403)

                if success:
                    jobs_count = stats.get("jobs_extracted", 0)
                    self.stats_metrics["companies_crawled"] += 1
                    self.stats_metrics["jobs_extracted"] += jobs_count
                    self.repos.company_state.update_success(provider_id, company_id, {
                        "previous_jobs": 0,
                        "current_jobs": jobs_count,
                        "job_delta": jobs_count,
                        "next_crawl_offset": 8 * 3600,
                        "crawl_tier": "NORMAL",
                        "crawl_interval_hours": 8,
                        "rolling_churn_percent": 0.0,
                        "crawls_in_current_tier": 1,
                        "decision_reason": "ADAPTIVE_SUCCESS"
                    })
                else:
                    self.repos.company_state.update_failure(provider_id, company_id, {
                        "status": "QUEUED",
                        "next_check_at": time.time() + 7200
                    })

        sub_tasks = [_crawl_single() for _ in range(batch_size)]
        await asyncio.gather(*sub_tasks, return_exceptions=True)

if __name__ == "__main__":
    worker = AdaptiveCrawlerWorker()
    worker.run()
