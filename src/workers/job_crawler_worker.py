import os
import sys
import time
import json
import logging
import asyncio
from src.workers.worker_base import BaseWorker
from src.discovery.pipeline.sync_session import BoardSyncSession
from src.discovery.models import Board, StandardBoardIdentity, WorkdayBoardIdentity, GreenhouseBoardIdentity, LeverBoardIdentity
from src.discovery.pipeline.repositories.reservation_repository import SQLiteReservationRepository
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JobCrawlerWorker")

def make_board_from_registry_row(row):
    ats_type = row["ats_type"].lower()
    endpoint = row["canonical_endpoint"] or row["endpoint"]
    metadata_str = row["ats_metadata"] or "{}"
    try:
        metadata = json.loads(metadata_str)
    except:
        metadata = {}
        
    if ats_type == "greenhouse":
        token = metadata.get("board_token") or endpoint.split("/")[-1]
        identity = GreenhouseBoardIdentity(ats="greenhouse", board_token=token)
    elif ats_type == "lever":
        token = metadata.get("board_token") or endpoint.split("/")[-1]
        identity = LeverBoardIdentity(ats="lever", board_token=token)
    elif ats_type == "workday":
        tenant = metadata.get("tenant") or endpoint.split("/")[-2]
        site = metadata.get("site") or "careers"
        identity = WorkdayBoardIdentity(ats="workday", tenant=tenant, site=site)
    else:
        token = metadata.get("board_token") or endpoint.split("/")[-1]
        identity = StandardBoardIdentity(ats=ats_type, board_token=token)
        
    return Board(
        identity=identity,
        endpoint=endpoint,
        provider=ats_type,
        discovered_by="ATSRegistry",
        discovered_at=row.get("created_at") or time.time(),
        last_verified_at=row.get("last_verified") or time.time(),
        metadata=metadata
    )

class JobCrawlerWorker(BaseWorker):
    def __init__(self):
        super().__init__("JobCrawlerWorker")
        self.repository = SQLiteReservationRepository(self.db_path)

    async def run_async(self):
        logger.info(f"JobCrawlerWorker starting as {self.worker_id}")
        while self.running:
            try:
                # 1. Pop from crawl_queue (if any explicit queue requests exist)
                q_item = self.queue.pop("crawl_queue")
                company_id = None
                q_token = None
                
                if q_item:
                    company_id = q_item["payload"].get("company_id")
                    item_id = q_item["_item_id"]
                    logger.info(f"Popped crawl job from queue: {company_id}")
                
                # 2. Reserve a due board using the Repository checkout
                row_data = None
                if company_id:
                    # Explicit queue item requested, lock it directly if active
                    import sqlite3
                    with sqlite3.connect(self.db_path) as conn:
                        conn.row_factory = sqlite3.Row
                        cursor = conn.execute("SELECT * FROM ats_registry WHERE company_id = ? AND status = 'ACTIVE'", (company_id,))
                        row = cursor.fetchone()
                        if row:
                            row_data = dict(row)
                            row_data["reservation_token"] = "QUEUE-EXPLICIT"
                else:
                    # Scan for due board
                    row_data = self.repository.reserve_due_board(self.worker_id, lock_duration=300)

                if not row_data:
                    # No work, update heartbeat and poll sleep
                    self.heartbeat()
                    await asyncio.sleep(settings.crawler_poll_interval)
                    continue

                company_id = row_data["company_id"]
                token = row_data.get("reservation_token")

                # 3. Construct Board and Connector sync
                board = make_board_from_registry_row(row_data)
                
                # Retrieve the Connector to check its CrawlPolicy
                connector = ConnectorRegistry.get(board.provider)
                if connector:
                    policy = connector.crawl_policy()
                    interval = policy.normal_interval
                else:
                    interval = settings.crawler_interval

                session = BoardSyncSession(board, db_path=self.db_path)
                logger.info(f"{self.worker_id} syncing jobs for {company_id} ({board.provider}) using policy interval {interval}s")
                
                start_time = time.time()
                await session.execute()
                latency = int((time.time() - start_time) * 1000)

                success = session.stats.get("success", False)
                job_count = session.stats.get("jobs_inserted", 0) + session.stats.get("jobs_updated", 0)

                # 4. Persistence managed exclusively by repository
                if success:
                    self.repository.mark_completed(company_id, token, interval)
                    
                    # Emit domain event
                    self.metrics.record_event("JobsSynced", {
                        "company_id": company_id,
                        "provider": board.provider,
                        "jobs_found": job_count,
                        "latency_ms": latency,
                        "worker_id": self.worker_id
                    })
                    
                    # Update metrics
                    self.metrics.update_business_metric("total_jobs_crawled", job_count)
                    self.metrics.update_operational_metric(f"{self.worker_id}:last_success", time.time())
                    self.metrics.update_operational_metric(f"{self.worker_id}:avg_latency", latency)
                else:
                    self.repository.mark_failed(company_id, token, settings.retry_schedule)
                    self.metrics.update_operational_metric(f"{self.worker_id}:last_failure", time.time())

                self.heartbeat(jobs_processed=job_count)
                
                if q_item:
                    self.queue.ack("crawl_queue", item_id)

                await asyncio.sleep(5)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in JobCrawlerWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                if q_item:
                    self.queue.nack("crawl_queue", item_id, reason=str(e))
                await asyncio.sleep(15)

        self.stop()
        logger.info("JobCrawlerWorker stopped.")

if __name__ == "__main__":
    worker = JobCrawlerWorker()
    asyncio.run(worker.run_async())
