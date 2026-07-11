"""
LinkedIn Pipeline B provider.

Wraps LinkedInJobsProvider using the JobBoardProvider interface.
Reads target roles and locations from src/config/user_preferences.yaml.
Requires APIFY_API_KEY — returns is_available()=False when absent.
"""

import time
import logging
from typing import Optional

from src.discovery.providers.job_board_provider import JobBoardProvider, JobBoardResult
from src.discovery.providers.base_provider import StandardJob

logger = logging.getLogger("LinkedInBoardProvider")


class LinkedInBoardProvider(JobBoardProvider):
    """Pipeline B adapter over the existing LinkedInJobsProvider."""

    @property
    def name(self) -> str:
        return "linkedin"

    def is_available(self) -> bool:
        try:
            from src.common.credential_provider import CredentialFactory
            creds = CredentialFactory.get("APIFY")
            return creds is not None
        except Exception:
            return False

    def _load_preferences(self) -> dict:
        try:
            import yaml
            with open("src/config/user_preferences.yaml", "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {
                "target_roles": ["Software Engineer", "Product Manager"],
                "locations": ["India", "Remote"],
            }

    def discover(self, cursor: Optional[str] = None) -> JobBoardResult:
        start = time.time()
        try:
            from src.discovery.providers.linkedin_jobs_provider import LinkedInJobsProvider
            provider = LinkedInJobsProvider()
            raw: list = provider._discover_jobs_internal(last_sync_timestamp=cursor)
            duration = int((time.time() - start) * 1000)
            return JobBoardResult(
                provider=self.name,
                jobs=raw if isinstance(raw, list) else [],
                next_cursor=None,   # LinkedIn provider returns full page; no cursor yet
                error=None,
                duration_ms=duration,
            )
        except Exception as e:
            logger.warning(f"LinkedInBoardProvider.discover() failed: {e}")
            return JobBoardResult(
                provider=self.name,
                jobs=[],
                next_cursor=cursor,
                error=str(e),
                duration_ms=int((time.time() - start) * 1000),
            )
