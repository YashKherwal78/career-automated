"""
Pipeline B — Job Board Worker.

Discovers jobs directly from job boards (LinkedIn, Google Jobs, etc.)
and writes them into normalized_jobs via the same CanonicalJob →
JobRepository.upsert_and_diff() path as Pipeline A.

Unknown companies found by job boards are enqueued into discovery_queue
so Pipeline A can discover their ATS endpoints and create authoritative
company records (the two pipelines reinforce each other).

Architecture:
  JobBoardRegistry.load()   → list of available providers
  provider.discover(cursor) → JobBoardResult[StandardJob]
  JobBoardNormalizer        → CanonicalJob
  JobRepository             → normalized_jobs (shared with Pipeline A)
  CompanyResolver           → discovery_queue (cross-feed to Pipeline A)
"""

import os
import sys
import time
import sqlite3
import logging

from src.workers.worker_base import BaseWorker
from src.config.settings import settings
from src.discovery.providers.job_board_registry import JobBoardRegistry
from src.discovery.pipeline.company_resolver import CompanyResolver
from src.discovery.pipeline.job_board_normalizer import JobBoardNormalizer
from src.discovery.pipeline.repositories.job import JobRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("JobBoardWorker")


class JobBoardWorker(BaseWorker):
    """
    Pipeline B worker. Runs independently of Pipeline A workers.
    One cycle = one pass over all available job board providers.
    """

    def __init__(self):
        super().__init__("JobBoardWorker")
        self.registry = JobBoardRegistry()
        self.job_repo = JobRepository(self.db_path)
        self.resolver = CompanyResolver(self.db_path, self.queue)
        self.normalizer = JobBoardNormalizer(self.resolver)

    # ── Public entry point ──────────────────────────────────────────────────

    def run(self):
        logger.info("JobBoardWorker starting.")
        while self.running:
            try:
                self._run_cycle()
                self.heartbeat()
                logger.info(
                    f"JobBoardWorker cycle complete. "
                    f"Sleeping {settings.pipeline_b_interval}s."
                )
                time.sleep(settings.pipeline_b_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"JobBoardWorker unhandled error: {e}", exc_info=True)
                self.heartbeat(failure_increment=1, last_error=str(e))
                time.sleep(60)
        self.stop()
        logger.info("JobBoardWorker stopped.")

    # ── Cycle ───────────────────────────────────────────────────────────────

    def _run_cycle(self):
        providers = self.registry.load()
        if not providers:
            logger.info("JobBoardWorker: no providers available (check API keys). Idling.")
            return

        for provider in providers:
            try:
                self._run_provider(provider)
            except Exception as e:
                # One provider failing must never stop the others
                logger.error(
                    f"JobBoardWorker: unhandled error in provider "
                    f"'{provider.name}': {e}",
                    exc_info=True,
                )

    def _run_provider(self, provider):
        logger.info(f"JobBoardWorker: starting sync for provider '{provider.name}'.")
        cursor = self._load_cursor(provider.name)

        result = provider.discover(cursor=cursor)

        if result.error:
            logger.warning(
                f"JobBoardWorker: provider '{provider.name}' returned error: {result.error}"
            )

        jobs_new = 0
        jobs_updated = 0
        companies_discovered = 0
        companies_seen_this_run = set()

        for std_job in result.jobs:
            canonical = self.normalizer.to_canonical(std_job, board_id=provider.name)
            if canonical is None:
                continue

            try:
                inserted, updated, _ = self.job_repo.upsert_and_diff(
                    [canonical], board_id=provider.name, synced_at=time.time()
                )
                jobs_new += inserted
                jobs_updated += updated
            except Exception as e:
                logger.warning(
                    f"JobBoardWorker: upsert failed for '{std_job.role}': {e}"
                )
                continue

            # Track unique companies discovered this run for cross-feed count
            domain_key = canonical.company_id
            if domain_key.startswith("pb_") and domain_key not in companies_seen_this_run:
                companies_seen_this_run.add(domain_key)
                companies_discovered += 1

        self._save_snapshot(
            provider_name=provider.name,
            next_cursor=result.next_cursor,
            jobs_found=result.jobs_found,
            jobs_new=jobs_new,
            jobs_updated=jobs_updated,
            companies_discovered=companies_discovered,
            status="SUCCESS" if not result.error else "PARTIAL",
            error=result.error,
        )

        logger.info(
            f"JobBoardWorker: '{provider.name}' — "
            f"{result.jobs_found} found, {jobs_new} new, "
            f"{jobs_updated} updated, {companies_discovered} companies fed to Pipeline A."
        )

    # ── Snapshot / cursor persistence ────────────────────────────────────────

    def _load_cursor(self, provider_name: str) -> str | None:
        """Load the last cursor stored for this provider (for incremental sync)."""
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                row = conn.execute(
                    """SELECT cursor FROM job_board_snapshots
                       WHERE provider = ? AND status IN ('SUCCESS', 'PARTIAL')
                       ORDER BY synced_at DESC LIMIT 1""",
                    (provider_name,),
                ).fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.warning(f"JobBoardWorker: could not load cursor for {provider_name}: {e}")
            return None

    def _save_snapshot(
        self,
        provider_name: str,
        next_cursor: str | None,
        jobs_found: int,
        jobs_new: int,
        jobs_updated: int,
        companies_discovered: int,
        status: str,
        error: str | None,
    ):
        try:
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                conn.execute(
                    """INSERT INTO job_board_snapshots
                       (provider, synced_at, cursor, jobs_found, jobs_new,
                        jobs_updated, companies_discovered, status, error)
                       VALUES (?, unixepoch('now'), ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        provider_name,
                        next_cursor,
                        jobs_found,
                        jobs_new,
                        jobs_updated,
                        companies_discovered,
                        status,
                        error,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"JobBoardWorker: failed to save snapshot for {provider_name}: {e}")


if __name__ == "__main__":
    worker = JobBoardWorker()
    worker.run()
