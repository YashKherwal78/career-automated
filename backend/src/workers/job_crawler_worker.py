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

# Import all connectors at startup to populate ConnectorRegistry
import src.discovery.connectors.greenhouse
import src.discovery.connectors.lever
import src.discovery.connectors.workday
import src.discovery.connectors.ashby
import src.discovery.connectors.smartrecruiters

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JobCrawlerWorker")

def make_board_from_registry_row(row):
    # --- Defensive field validation ---
    missing = [f for f in ("ats_type", "company_id") if f not in row or row[f] is None]
    if missing:
        raise ValueError(
            f"make_board_from_registry_row: registry row missing required fields {missing}. "
            f"Available keys: {list(row.keys())}"
        )

    ats_type = row["ats_type"].lower()
    endpoint = row.get("canonical_endpoint") or row.get("endpoint")
    if not endpoint:
        raise ValueError(
            f"make_board_from_registry_row: company '{row['company_id']}' has no endpoint or canonical_endpoint"
        )

    metadata_str = row.get("ats_metadata") or "{}"
    try:
        metadata = json.loads(metadata_str) if isinstance(metadata_str, str) else (metadata_str or {})
    except Exception:
        logger.warning(f"make_board_from_registry_row: failed to parse ats_metadata for {row.get('company_id')}, using empty dict")
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
    elif ats_type == "smartrecruiters":
        token = metadata.get("company_identifier") or metadata.get("board_token") or endpoint.split("/")[-1]
        identity = StandardBoardIdentity(ats=ats_type, board_token=token)
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
            q_item = None
            item_id = None
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
                    from src.api.db import get_connection, is_postgres
                    conn = get_connection()
                    try:
                        if is_postgres():
                            cursor = conn.execute("SELECT * FROM ats_registry WHERE company_id = %s AND status = 'ACTIVE'", (company_id,))
                        else:
                            cursor = conn.execute("SELECT * FROM ats_registry WHERE company_id = ? AND status = 'ACTIVE'", (company_id,))
                        row = cursor.fetchone()
                        if row:
                            row_data = dict(row)
                            row_data["reservation_token"] = "QUEUE-EXPLICIT"
                    finally:
                        conn.close()
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
                run_id = f"crawl-run-{company_id}-{int(time.time())}"
                from src.discovery.pipeline.telemetry import Telemetry, Stage, Status, ReasonCode
                Telemetry.start_run(run_id, "JobCrawlerWorker", trigger="Cron")
                
                logger.info(f"{self.worker_id} syncing jobs for {company_id} ({board.provider}) using policy interval {interval}s")
                
                start_time = time.time()
                try:
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
                        
                        Telemetry.record_event(
                            stage=Stage.CRAWL_EXECUTED,
                            status=Status.SUCCESS,
                            run_id=run_id,
                            company_id=company_id,
                            worker_name="JobCrawlerWorker",
                            ats_type=board.provider,
                            latency_ms=latency,
                            reason_code=ReasonCode.NONE,
                            metadata={"jobs_synced": job_count}
                        )
                        
                        if job_count > 0:
                            Telemetry.record_event(
                                stage=Stage.NORMALIZATION_EXECUTED,
                                status=Status.SUCCESS,
                                run_id=run_id,
                                company_id=company_id,
                                worker_name="JobCrawlerWorker",
                                ats_type=board.provider,
                                reason_code=ReasonCode.NONE,
                                metadata={"jobs_normalized": job_count}
                            )
                        
                        Telemetry.finish_run(run_id, Status.SUCCESS)
                    else:
                        self.repository.mark_failed(company_id, token, settings.retry_schedule)
                        self.metrics.update_operational_metric(f"{self.worker_id}:last_failure", time.time())
                        
                        Telemetry.record_event(
                            stage=Stage.CRAWL_EXECUTED,
                            status=Status.FAILURE,
                            run_id=run_id,
                            company_id=company_id,
                            worker_name="JobCrawlerWorker",
                            ats_type=board.provider,
                            latency_ms=latency,
                            reason_code=ReasonCode.INSPECTOR_FAILED
                        )
                        Telemetry.finish_run(run_id, Status.SUCCESS)
                except Exception as ex:
                    Telemetry.finish_run(run_id, Status.FAILURE)
                    raise ex

                self.heartbeat(jobs_processed=job_count)
                
                if q_item:
                    self.queue.ack("crawl_queue", item_id)

                await asyncio.sleep(5)

            except KeyboardInterrupt:
                break
            except Exception as e:
                import traceback
                logger.error(f"Error in JobCrawlerWorker loop: {e}\n{traceback.format_exc()}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                self.metrics.record_event("CrawlFailed", {
                    "company_id": company_id if 'company_id' in locals() else "unknown",
                    "error": str(e),
                    "worker_id": self.worker_id
                })
                if q_item and item_id:
                    self.queue.nack("crawl_queue", item_id, reason=str(e))
                await asyncio.sleep(15)

        self.stop()
        logger.info("JobCrawlerWorker stopped.")

if __name__ == "__main__":
    worker = JobCrawlerWorker()
    asyncio.run(worker.run_async())
