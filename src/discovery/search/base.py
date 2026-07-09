from abc import ABC, abstractmethod
from typing import List
from src.discovery.search.models import SearchResult

class SearchProvider(ABC):
    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        pass
