import asyncio
import logging
from src.discovery.models import Board, StandardBoardIdentity
from src.discovery.pipeline.repositories.board import BoardRepository
from src.discovery.pipeline.scheduler import Scheduler

logging.basicConfig(level=logging.INFO)

async def main():
    db_path = "test_phase5.db"
    
    # 1. Init repo and insert test boards
    repo = BoardRepository(db_path)
    
    # Board 1: Figma (Greenhouse)
    identity_gh = StandardBoardIdentity(ats="greenhouse", board_token="figma")
    board_gh = Board(
        identity=identity_gh,
        endpoint="https://boards.greenhouse.io/figma",
        provider="greenhouse",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    
    # Board 2: Notion (Lever)
    identity_lv = StandardBoardIdentity(ats="lever", board_token="notion")
    board_lv = Board(
        identity=identity_lv,
        endpoint="https://jobs.lever.co/notion",
        provider="lever",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    
    # Note: add will default next_sync_at to 0.0, making them immediately due
    repo.add(board_gh)
    repo.add(board_lv)
    print("✅ Inserted 2 test boards into repository.")
    
    # 2. Run scheduler
    scheduler = Scheduler(db_path, max_concurrent=2)
    print("🚀 Starting Scheduler...")
    await scheduler.run()

if __name__ == "__main__":
    import src.discovery.connectors.greenhouse
    import src.discovery.connectors.lever
    
    asyncio.run(main())
