"""
mass_scheduler.py — High-concurrency async mass crawl scheduler.

Architecture:
  - Reads from production ats_registry (PostgreSQL) via reserve_due_board() CTE checkout.
  - Runs many concurrent async tasks per provider (MASS_CONCURRENCY env var).
  - Performs lease renewal every 90 seconds to prevent stale-worker fencing.
  - On success: marks board completed, writes JobSynced event to outbox.
  - On failure: marks board failed with exponential backoff, writes CrawlFailed event.
  - Graceful SIGINT/SIGTERM drain: stops reserving new work, waits for active tasks.
  - No SQLite, no subprocess management, no legacy provider tables.
"""

import asyncio
import time
import os
import sys
import logging
import signal
import datetime
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from src.discovery.pipeline.sync_session import BoardSyncSession
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.workers.job_crawler_worker import make_board_from_registry_row
from src.core.repositories.company.state import CompanyStateRepository
from src.core.repositories.outbox.repository import OutboxRepository
from src.config.settings import settings

# ── Bootstrap all connectors at startup ──────────────────────────────────────
# Uses dynamic discovery so every module in src/discovery/connectors/ is
# imported automatically. Adding a new connector = dropping in a file.
from src.discovery.connectors.bootstrap import bootstrap_connectors
_discovered, _imported = bootstrap_connectors()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("MassScheduler")

# ── Configuration ─────────────────────────────────────────────────────────────
# How many concurrent crawl coroutines to run in total
MASS_CONCURRENCY = int(os.environ.get("MASS_CONCURRENCY", "20"))

# Lease duration for each board reservation (seconds)
LEASE_DURATION = int(os.environ.get("LEASE_DURATION", "300"))

# Lease renewal fires every N seconds (must be < LEASE_DURATION)
LEASE_RENEW_INTERVAL = int(os.environ.get("LEASE_RENEW_INTERVAL", "90"))

# Poll interval when no boards are available
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))

# Filter to a specific provider (optional)
PROVIDER_FILTER = os.environ.get("PROVIDER_FILTER", None)

# ── Global shutdown flag ───────────────────────────────────────────────────────
_draining = False


def _handle_stop(signum, frame):
    global _draining
    logger.info(f"[MassScheduler] Received signal {signum}. Draining — no new work will be reserved.")
    _draining = True


signal.signal(signal.SIGINT, _handle_stop)
signal.signal(signal.SIGTERM, _handle_stop)


# ── Lease renewal helper ───────────────────────────────────────────────────────
async def _renew_lease_loop(company_id: str, lease_token: str, stop_event: asyncio.Event):
    """Renews the lease for company_id every LEASE_RENEW_INTERVAL seconds.
    Sets stop_event on failure so the crawler knows it has lost the lease."""
    state_repo = CompanyStateRepository()
    while not stop_event.is_set():
        # Sleep in 1-second ticks so we can react to stop_event quickly
        for _ in range(LEASE_RENEW_INTERVAL):
            if stop_event.is_set():
                return
            await asyncio.sleep(1)

        if stop_event.is_set():
            return

        try:
            new_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=LEASE_DURATION)
            with state_repo.transaction() as conn:
                cur = conn.execute(
                    """
                    UPDATE ats_registry
                    SET reserved_until_tz = %s
                    WHERE company_id = %s AND lease_token = %s
                    """,
                    (new_expiry, company_id, lease_token),
                )
                if cur.rowcount == 0:
                    logger.error(f"[{company_id}] Lease renewal failed — lease token lost! Aborting crawl.")
                    stop_event.set()
                    return
            logger.debug(f"[{company_id}] Lease renewed until {new_expiry.isoformat()}")
        except Exception as exc:
            logger.error(f"[{company_id}] Lease renewal exception: {exc}")
            stop_event.set()
            return


# ── Per-board crawl coroutine ──────────────────────────────────────────────────
async def _crawl_board(row_data: dict, worker_id: str):
    """Crawls one board. Handles lease renewal, outbox events, and state updates."""
    company_id = row_data["company_id"]
    lease_token = row_data.get("lease_token") or row_data.get("reservation_token")
    provider = row_data.get("provider_id") or row_data.get("ats_type", "unknown")

    state_repo = CompanyStateRepository()
    outbox_repo = OutboxRepository()

    logger.info(f"[{worker_id}] Crawling {company_id} ({provider})")

    # Build Board object
    try:
        board = make_board_from_registry_row(row_data)
    except Exception as exc:
        logger.error(f"[{company_id}] Failed to build board: {exc}")
        try:
            state_repo.mark_failed(company_id, lease_token, settings.retry_schedule)
        except Exception:
            pass
        return

    # Start lease renewal
    stop_event = asyncio.Event()
    renewal_task = asyncio.create_task(_renew_lease_loop(company_id, lease_token, stop_event))

    session = BoardSyncSession(board, db_path=settings.db_path)
    start_ts = time.time()

    try:
        # Run sync — monitor for lease loss
        sync_task = asyncio.create_task(session.execute())
        while not sync_task.done():
            if stop_event.is_set():
                sync_task.cancel()
                logger.error(f"[{company_id}] Sync cancelled — lease was lost.")
                break
            await asyncio.sleep(0.5)

        if not stop_event.is_set():
            await sync_task  # propagate any exception

        if stop_event.is_set():
            raise RuntimeError(f"Crawl aborted: lease lost for {company_id}")

        latency_ms = int((time.time() - start_ts) * 1000)
        success = session.stats.get("success", False)
        jobs_inserted = session.stats.get("jobs_inserted", 0)
        jobs_updated = session.stats.get("jobs_updated", 0)
        job_count = jobs_inserted + jobs_updated

        # Determine crawl interval from connector policy
        connector = ConnectorRegistry.get(board.provider)
        if connector:
            try:
                policy = connector.crawl_policy()
                interval_secs = policy.normal_interval
            except Exception:
                interval_secs = settings.crawler_interval
        else:
            interval_secs = settings.crawler_interval

        if success:
            with state_repo.transaction():
                state_repo.mark_completed(company_id, lease_token, interval_secs)
                outbox_repo.save_event(
                    event_type="JobSynced",
                    aggregate_type="Company",
                    aggregate_id=company_id,
                    payload={
                        "company_id": company_id,
                        "provider": provider,
                        "jobs_found": job_count,
                        "jobs_inserted": jobs_inserted,
                        "jobs_updated": jobs_updated,
                        "latency_ms": latency_ms,
                        "worker_id": worker_id,
                    },
                )
            logger.info(
                f"[{worker_id}] ✓ {company_id} — {job_count} jobs "
                f"({jobs_inserted} new, {jobs_updated} updated) in {latency_ms}ms"
            )
        else:
            failure_reason = session.stats.get("error_message", "SYNC_EXECUTION_FAILURE")
            with state_repo.transaction():
                state_repo.mark_failed(company_id, lease_token, settings.retry_schedule)
                outbox_repo.save_event(
                    event_type="CrawlFailed",
                    aggregate_type="Company",
                    aggregate_id=company_id,
                    payload={
                        "company_id": company_id,
                        "provider": provider,
                        "failure_reason": failure_reason,
                        "latency_ms": latency_ms,
                        "worker_id": worker_id,
                    },
                )
            logger.warning(f"[{worker_id}] ✗ {company_id} — crawl failed: {failure_reason}")

    except asyncio.CancelledError:
        logger.warning(f"[{company_id}] Crawl task was externally cancelled.")
        try:
            state_repo.mark_failed(company_id, lease_token, settings.retry_schedule)
        except Exception:
            pass

    except Exception as exc:
        latency_ms = int((time.time() - start_ts) * 1000)
        logger.error(f"[{company_id}] Unhandled crawl exception: {exc}\n{traceback.format_exc()}")
        try:
            with state_repo.transaction():
                state_repo.mark_failed(company_id, lease_token, settings.retry_schedule)
                outbox_repo.save_event(
                    event_type="CrawlFailed",
                    aggregate_type="Company",
                    aggregate_id=company_id,
                    payload={
                        "company_id": company_id,
                        "provider": provider,
                        "failure_reason": str(exc)[:500],
                        "latency_ms": latency_ms,
                        "worker_id": worker_id,
                    },
                )
        except Exception:
            pass

    finally:
        stop_event.set()
        try:
            await renewal_task
        except Exception:
            pass


# ── Main scheduler loop ────────────────────────────────────────────────────────
async def scheduler_main():
    global _draining

    worker_prefix = f"mass-{os.getpid()}"
    logger.info(
        f"[MassScheduler] Starting — concurrency={MASS_CONCURRENCY}, "
        f"provider_filter={PROVIDER_FILTER or 'ALL'}, lease={LEASE_DURATION}s"
    )

    state_repo = CompanyStateRepository()
    active_tasks: set[asyncio.Task] = set()
    task_counter = 0

    stats = {
        "reserved": 0,
        "succeeded": 0,
        "failed": 0,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    last_log_ts = time.time()

    while not _draining:
        # ── Fill up to MASS_CONCURRENCY active tasks ─────────────────────────
        while len(active_tasks) < MASS_CONCURRENCY and not _draining:
            task_counter += 1
            worker_id = f"{worker_prefix}-w{task_counter:04d}"

            row = state_repo.reserve_due_board(
                worker_id=worker_id,
                provider_id=PROVIDER_FILTER,
                lock_duration=LEASE_DURATION,
            )

            if not row:
                # No boards available right now
                break

            stats["reserved"] += 1

            async def _run(r=row, wid=worker_id):
                try:
                    await _crawl_board(r, wid)
                    stats["succeeded"] += 1
                except Exception:
                    stats["failed"] += 1

            task = asyncio.create_task(_run())
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)

        # ── Periodic progress log ────────────────────────────────────────────
        now = time.time()
        if now - last_log_ts >= 30:
            logger.info(
                f"[MassScheduler] Status — active={len(active_tasks)}, "
                f"reserved={stats['reserved']}, "
                f"succeeded={stats['succeeded']}, "
                f"failed={stats['failed']}"
            )
            last_log_ts = now

        # ── Sleep briefly before next fill check ─────────────────────────────
        if active_tasks:
            # Wait for at least one task to finish or poll timeout
            done, _ = await asyncio.wait(
                active_tasks, timeout=POLL_INTERVAL, return_when=asyncio.FIRST_COMPLETED
            )
        else:
            # No active tasks, no boards — wait before polling again
            logger.info(f"[MassScheduler] No boards due. Sleeping {POLL_INTERVAL}s...")
            await asyncio.sleep(POLL_INTERVAL)

    # ── Drain: wait for all active tasks to finish ───────────────────────────
    if active_tasks:
        logger.info(f"[MassScheduler] Draining {len(active_tasks)} active tasks...")
        await asyncio.gather(*active_tasks, return_exceptions=True)

    logger.info(
        f"[MassScheduler] Shutdown complete. "
        f"Total reserved={stats['reserved']}, "
        f"succeeded={stats['succeeded']}, "
        f"failed={stats['failed']}"
    )


if __name__ == "__main__":
    asyncio.run(scheduler_main())
