from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Dict, Any
from src.discovery.models import Board, RawJob, ConnectorCapability, FetchResult

class FreshnessStrategy(ABC):
    @abstractmethod
    def should_sync(self, board: Board, fetch_result: FetchResult) -> bool:
        """Determines if the payload is fresh enough to skip synchronization."""
        pass

class DefaultFreshnessStrategy(FreshnessStrategy):
    """Fallback strategy that relies purely on SHA256 content hashing."""
    def should_sync(self, board: Board, fetch_result: FetchResult) -> bool:
        # If the server explicitly says 304, definitely skip
        if fetch_result.status_code == 304:
            return False
            
        # If we have a content_hash in the board metadata, check it
        stored_hash = board.metadata.get("content_hash")
        if stored_hash and stored_hash == fetch_result.content_hash:
            return False
            
        return True

from enum import Enum
from dataclasses import dataclass, field

class CrawlPriority(Enum):
    CRITICAL = 100
    HIGH = 50
    NORMAL = 10
    LOW = 1

@dataclass
class CrawlPolicy:
    version: str = "v1"
    normal_interval: int = 120 # default 2 minutes
    retry_schedule: list = field(default_factory=lambda: [300, 900, 1800, 3600, 21600, 86400])
    priority: CrawlPriority = CrawlPriority.NORMAL
    supports_incremental: bool = True
    supports_webhooks: bool = False
    max_parallel: int = 5
    timeout: int = 30
    rate_limit: int = 5

class Connector(ABC):
    """
    Base interface for ATS Connectors.
    A Connector strictly handles provider communication protocol and pagination.
    """
    
    @abstractmethod
    def capabilities(self) -> ConnectorCapability:
        pass

    def crawl_policy(self) -> CrawlPolicy:
        """Returns the crawl policy configuration for this connector."""
        return CrawlPolicy()
        
    def freshness_strategy(self) -> FreshnessStrategy:
        """Returns the freshness strategy for this connector. Defaults to content hash fallback."""
        return DefaultFreshnessStrategy()
        
    @abstractmethod
    async def sync(self, board: Board, http_client: Any) -> AsyncIterator[RawJob | FetchResult]:
        """
        Yields RawJobs incrementally. The connector owns its own pagination.
        """
        yield # pragma: no cover
