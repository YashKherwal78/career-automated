import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class DiscoveredCompany:
    company_name: str
    website: str
    domain: str
    country: str = "Global"
    source: str = "Unknown"
    source_url: str = ""
    discovered_at: float = field(default_factory=time.time)
    source_confidence: float = 1.0
    discovery_priority: str = "P1"

class BaseDiscoveryPlugin(ABC):
    @property
    @abstractmethod
    def plugin_name(self) -> str:
        pass

    @property
    @abstractmethod
    def priority_tier(self) -> str:
        pass

    @abstractmethod
    async def discover(self) -> List[DiscoveredCompany]:
        pass
