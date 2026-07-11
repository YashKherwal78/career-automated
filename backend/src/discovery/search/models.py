from dataclasses import dataclass

@dataclass
class SearchResult:
    provider: str
    query: str
    title: str
    url: str
    snippet: str
    rank: int
    latency_ms: int
