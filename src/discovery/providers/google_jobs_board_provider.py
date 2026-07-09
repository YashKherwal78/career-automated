"""
Google Jobs Pipeline B provider.

Wraps GoogleJobsProvider using the JobBoardProvider interface.
Reads target roles and locations from src/config/user_preferences.yaml.
Requires APIFY_API_KEY — returns is_available()=False when absent.
"""

import time
import logging
from typing import Optional

from src.discovery.providers.job_board_provider import JobBoardProvider, JobBoardResult

logger = logging.getLogger("GoogleJobsBoardProvider")


class GoogleJobsBoardProvider(JobBoardProvider):
    """Pipeline B adapter over the existing GoogleJobsProvider."""

    @property
    def name(self) -> str:
        return "google_jobs"

    def is_available(self) -> bool:
        try:
            from src.common.credential_provider import CredentialFactory
            creds = CredentialFactory.get("APIFY")
            return creds is not None
        except Exception:
            return False

    def discover(self, cursor: Optional[str] = None) -> JobBoardResult:
        start = time.time()
        try:
            from src.discovery.providers.google_jobs_provider import GoogleJobsProvider
            provider = GoogleJobsProvider()
            raw: list = provider._discover_jobs_internal(last_sync_timestamp=cursor)
            duration = int((time.time() - start) * 1000)
            return JobBoardResult(
                provider=self.name,
                jobs=raw if isinstance(raw, list) else [],
                next_cursor=None,
                error=None,
                duration_ms=duration,
            )
        except Exception as e:
            logger.warning(f"GoogleJobsBoardProvider.discover() failed: {e}")
            return JobBoardResult(
                provider=self.name,
                jobs=[],
                next_cursor=cursor,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )
