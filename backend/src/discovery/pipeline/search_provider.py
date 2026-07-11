from typing import List, Protocol

class SearchResult:
    def __init__(self, url: str, title: str, snippet: str):
        self.url = url
        self.title = title
        self.snippet = snippet

class SearchProvider(Protocol):
    async def search(self, query: str) -> List[SearchResult]:
        ...

class MockSearchProvider:
    async def search(self, query: str) -> List[SearchResult]:
        # Return mock results for testing
        return []
