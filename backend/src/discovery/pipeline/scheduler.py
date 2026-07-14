import asyncio
import time
import logging
from typing import List
from src.discovery.models import Board
from src.discovery.pipeline.repositories.board import BoardRepository
from src.discovery.pipeline.sync_session import BoardSyncSession

logger = logging.getLogger("Scheduler")

class Scheduler:
    def __init__(self, db_path: str, max_concurrent: int = 5):
        self.db_path = db_path
        self.board_repo = BoardRepository(db_path)
        self.max_concurrent = max_concurrent
        self.sync_interval_seconds = 3600 * 12 # 12 hours by default

    async def _worker(self, queue: asyncio.Queue):
        while True:
            board = await queue.get()
            try:
                logger.info(f"Worker picking up {board.endpoint}")
                session = BoardSyncSession(board, self.db_path)
                stats = await session.execute()
                
                # Calculate next sync time based on success
                current_time = time.time()
                next_sync = current_time + self.sync_interval_seconds
                if not stats.get("success"):
                    # Retry sooner if failed
                    next_sync = current_time + 3600 # 1 hour
                    
                # Update board repo metadata and next sync time
                # Update freshness hashes, etags inside board.metadata
                board_id = board.identity.get_hash() if hasattr(board.identity, 'get_hash') else getattr(board.identity, 'board_token', board.endpoint)
                self.board_repo.update_sync_status(
                    board_id=board_id,
                    last_sync_at=current_time,
                    next_sync_at=next_sync,
                    new_metadata=board.metadata
                )
                
            except Exception as e:
                logger.error(f"Failed to sync {board.endpoint}: {e}")
            finally:
                queue.task_done()

    async def run(self, limit: int = 100, required_capabilities: dict = None, exclude_capabilities: dict = None):
        current_time = time.time()
        logger.info(f"Fetching boards due for sync...")
        boards = self.board_repo.get_due_boards(current_time, limit)
        
        # Capability Routing: Filter boards based on connector capabilities
        if required_capabilities or exclude_capabilities:
            from src.discovery.registry.connector_registry import ConnectorRegistry
            req = required_capabilities or {}
            exc = exclude_capabilities or {}
            
            allowed_providers = set()
            for provider in ConnectorRegistry._registry.keys():
                strategies = ConnectorRegistry.get_all_strategies(provider)
                if not strategies:
                    continue
                # We check the capabilities of the highest priority strategy
                connector = strategies[0].connector_class()
                caps = connector.capabilities()
                
                matches = True
                for flag, val in req.items():
                    if getattr(caps, flag, None) != val:
                        matches = False
                        break
                for flag, val in exc.items():
                    if getattr(caps, flag, None) == val:
                        matches = False
                        break
                        
                if matches:
                    allowed_providers.add(provider)
                    
            boards = [b for b in boards if b.provider in allowed_providers]
        
        if not boards:
            logger.info("No boards due for sync at this time.")
            return

        logger.info(f"Found {len(boards)} boards to sync. Starting {self.max_concurrent} workers.")
        
        queue = asyncio.Queue()
        for board in boards:
            queue.put_nowait(board)

        workers = []
        for _ in range(self.max_concurrent):
            workers.append(asyncio.create_task(self._worker(queue)))

        await queue.join()

        for w in workers:
            w.cancel()
            
        logger.info(f"Scheduler finished processing {len(boards)} boards.")
