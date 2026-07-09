import asyncio
import json
from src.discovery.pipeline.registry import BoardRegistry
from src.discovery.registry.source_registry import SourceRegistry

class BoardIngestionEngine:
    def __init__(self, db_path: str = "boards.db"):
        self.registry = BoardRegistry(db_path)
        
    async def ingest_all(self):
        boards = self.registry.get_active_boards()
        
        for board_row in boards:
            company_name = board_row['company_name']
            endpoint = board_row['endpoint']
            provider = board_row['provider']
            
            adapter = SourceRegistry.find_adapter_for_url(endpoint)
            if not adapter:
                continue
                
            try:
                # 1. Fetch raw data
                raw_data = await adapter.fetch({"url": endpoint, "company_id": company_name})
                
                # 2. Parse data
                parsed_data = adapter.parse(raw_data)
                
                # 3. Extract Jobs
                jobs = adapter.discover_jobs(parsed_data)
                
                print(f"Extracted {len(jobs)} jobs from {company_name} ({provider})")
                
                # 4. Normalization and JobIdentity Deduplication will go here
                
            except Exception as e:
                print(f"Failed to ingest from {endpoint}: {e}")

