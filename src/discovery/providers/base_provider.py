from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.discovery.models import Candidate

class DiscoveryStrategy(ABC):
    """
    Abstract interface for Discovery Strategies.

    A strategy's sole job is to return candidate URLs for a given company.
    It has ZERO knowledge of ATS platforms. ATS detection is the sole
    responsibility of SourceRegistry.find_adapter_for_url().

    Strategies are tried in priority order by the DiscoveryOrchestrator:
        1. WebsiteCrawlerStrategy  (direct domain scraping)
        2. SearchStrategy          (search engine fallback)
        3. Future strategies        (public datasets, APIs, etc.)
    """

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Unique name for this strategy, e.g. 'website_crawler'."""
        pass

    @abstractmethod
    async def discover(self, company_name: str, website_url: Optional[str] = None) -> List[Candidate]:
        """
        Returns a list of Candidate objects that might contain career/ATS endpoints.
        """
        pass


# Backwards-compatible alias so existing code doesn't break
BaseProvider = DiscoveryStrategy
