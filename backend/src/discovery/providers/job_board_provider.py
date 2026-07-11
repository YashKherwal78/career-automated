"""
Pipeline B — Job Board Provider base interface.

All Pipeline B providers implement JobBoardProvider. The worker loops over
whatever JobBoardRegistry.load() returns and never names providers directly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
from src.discovery.providers.base_provider import StandardJob


@dataclass
class JobBoardResult:
    """Returned by every JobBoardProvider.discover() call."""
    provider: str
    jobs: List[StandardJob]
    next_cursor: Optional[str]   # page token / etag / offset for incremental sync
    error: Optional[str]
    duration_ms: int
    jobs_found: int = 0

    def __post_init__(self):
        self.jobs_found = len(self.jobs)


class JobBoardProvider(ABC):
    """
    Abstract base for all Pipeline B providers.

    Implementations must:
      - Return False from is_available() when credentials are absent
        (the worker skips them gracefully — no exception raised).
      - Never raise from discover() — capture errors inside JobBoardResult.
      - Accept an optional cursor for incremental / paginated syncs.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name, e.g. 'linkedin', 'google_jobs'."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """
        Returns True only when all required credentials/config are present.
        Workers call this before discover() — a False result is a graceful skip.
        """
        ...

    @abstractmethod
    def discover(self, cursor: Optional[str] = None) -> JobBoardResult:
        """
        Fetch a batch of jobs from this job board.

        Args:
            cursor: Optional pagination token from the previous sync.

        Returns:
            JobBoardResult with jobs, next_cursor for the following sync,
            and any error message. Never raises.
        """
        ...
