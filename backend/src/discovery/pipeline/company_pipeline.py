import asyncio
import time
from typing import List
from dataclasses import dataclass

from src.discovery.models import Board
from src.discovery.providers.provider_registry import ProviderRegistry
from src.discovery.registry.source_registry import SourceRegistry
from urllib.parse import urlparse, urlunparse

@dataclass
class PipelineResult:
    company_name: str
    discovered_boards: List[Board]
    metrics: dict

class CompanyPipeline:
    """
    Orchestrates the discovery and verification of boards for a single company.
    It does NOT extract jobs. It purely outputs verified Board identities.
    """
    
    @staticmethod
    def canonicalize(url: str) -> str:
        parsed = urlparse(url)
        clean = parsed._replace(query="", fragment="")
        return urlunparse(clean).rstrip('/')

    @classmethod
    async def run(cls, company_name: str, website_url: str) -> PipelineResult:
        metrics = {
            "strategies_run": 0,
            "candidates_emitted": 0,
            "unique_endpoints": 0,
            "verified_boards": 0,
            "latency": 0.0
        }
        
        start_time = time.time()
        
        # 1. Discovery Phase
        providers = ProviderRegistry.get_all_providers()
        strategies = [p for p in providers.values()]
        metrics["strategies_run"] = len(strategies)
        
        discovered_candidates = []
        for strategy in strategies:
            try:
                if hasattr(strategy, 'discover'):
                    urls = await strategy.discover(company_name, website_url)
                    for c in urls:
                        c.source = strategy.strategy_name
                        discovered_candidates.append(c)
            except Exception:
                pass
                
        metrics["candidates_emitted"] = len(discovered_candidates)
        
        # 2. Normalization & Deduplication Phase
        unique_candidates = {}
        for c in discovered_candidates:
            clean_url = cls.canonicalize(c.url)
            if clean_url not in unique_candidates:
                unique_candidates[clean_url] = c
                
        metrics["unique_endpoints"] = len(unique_candidates)
        
        # 3. Identification Phase
        identified = []
        for clean_url, c in unique_candidates.items():
            adapter = SourceRegistry.find_adapter_for_url(clean_url)
            if adapter:
                identified.append((clean_url, c, adapter.source_name))
                
        # 4. Inspection & Verification Phase
        async def inspect(clean_url, c, adapter_name):
            inspector = SourceRegistry.get_inspector(adapter_name)
            inspection = await inspector.inspect_board(clean_url)
            
            # Identity Verification Policy
            is_valid = inspection.board_exists and inspection.api_verified
            if is_valid:
                # Naive canonical matching (can be expanded later)
                # But for now, if api_verified is true, we trust the board exists.
                pass
            
            return (is_valid, inspection, adapter_name, c)

        tasks = [inspect(url, c, adapter) for url, c, adapter in identified]
        results = await asyncio.gather(*tasks)
        
        # 5. Build Board Objects
        boards = []
        for is_valid, inspection, adapter_name, candidate in results:
            if is_valid and getattr(inspection, 'identity', None):
                board = Board(
                    identity=inspection.identity,
                    endpoint=inspection.endpoint,
                    provider=adapter_name,
                    discovered_by=candidate.source,
                    discovered_at=time.time(),
                    last_verified_at=time.time()
                )
                boards.append(board)
                
        metrics["verified_boards"] = len(boards)
        metrics["latency"] = time.time() - start_time
        
        return PipelineResult(
            company_name=company_name,
            discovered_boards=boards,
            metrics=metrics
        )
