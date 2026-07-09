from abc import ABC, abstractmethod
from typing import List, Dict, Any

class SeedSource(ABC):
    name: str
    priority: int
    enabled: bool

    @abstractmethod
    async def discover(self) -> List[Dict[str, Any]]:
        """
        Discovers new company seeds.
        Returns a list of dicts:
        {
            'company_id': str,
            'name': str,
            'website': str,
            'source': str,
            'confidence': float
        }
        """
        pass
