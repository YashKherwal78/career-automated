import asyncio
import sqlite3
import src.discovery.workers.greenhouse_adapter
import src.discovery.workers.lever_adapter
import src.discovery.workers.ashby_adapter
import src.discovery.workers.workday_adapter
import src.discovery.workers.smartrecruiters_adapter

from src.discovery.models import Board, StandardBoardIdentity, BoardSyncTask
from src.discovery.pipeline.scheduler import Scheduler

# We need to mock _resolve_board in Scheduler for testing
class TestScheduler(Scheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_boards = {}
        
    def add_mock_board(self, board_id, board):
        self.mock_boards[board_id] = board
        
    def _resolve_board(self, board_id: str):
        return self.mock_boards.get(board_id)

async def main():
    db_path = "test_phase5.db"
    
    # Clean up DB before test
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS jobs")
        conn.execute("DROP TABLE IF EXISTS board_syncs")
        conn.execute("DROP TABLE IF EXISTS board_snapshots")
        conn.commit()
    
    scheduler = TestScheduler(max_concurrency=2, db_path=db_path)
    
    # Add Figma (Greenhouse)
    figma_ident = StandardBoardIdentity(ats="greenhouse", board_token="figma")
    figma_board = Board(
        identity=figma_ident,
        endpoint="https://boards.greenhouse.io/figma",
        provider="greenhouse",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    scheduler.add_mock_board("figma", figma_board)
    scheduler.enqueue_task(BoardSyncTask(board_id="figma", priority=1, scheduled_at=0, retry_count=0))
    
    # Add Spotify (Lever)
    spotify_ident = StandardBoardIdentity(ats="lever", board_token="spotify")
    spotify_board = Board(
        identity=spotify_ident,
        endpoint="https://jobs.lever.co/spotify",
        provider="lever",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    scheduler.add_mock_board("spotify", spotify_board)
    scheduler.enqueue_task(BoardSyncTask(board_id="spotify", priority=1, scheduled_at=0, retry_count=0))
    
    print("🚀 Running Concurrent Scheduler (First Pass)")
    await scheduler.run()
    
    print("\n🔍 Verifying Database (First Pass)...")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) as c FROM jobs")
        print(f"  Jobs found: {cursor.fetchone()[0]}")
        cursor = conn.execute("SELECT COUNT(*) as c FROM board_syncs")
        print(f"  Sync logs found: {cursor.fetchone()[0]}")
        cursor = conn.execute("SELECT id, jobs_inserted, jobs_updated FROM board_syncs")
        for row in cursor.fetchall():
            print(f"  Sync: {row[0]} -> Inserted: {row[1]}, Updated: {row[2]}")
            
    print("\n🚀 Running Concurrent Scheduler (Second Pass - Should trigger 304 / Content Hash)")
    # Enqueue them again
    scheduler.enqueue_task(BoardSyncTask(board_id="figma", priority=1, scheduled_at=0, retry_count=0))
    scheduler.enqueue_task(BoardSyncTask(board_id="spotify", priority=1, scheduled_at=0, retry_count=0))
    await scheduler.run()
    
    print("\n🔍 Verifying Database (Second Pass)...")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) as c FROM jobs")
        print(f"  Jobs found: {cursor.fetchone()[0]}")
        cursor = conn.execute("SELECT id, jobs_inserted, jobs_updated, jobs_extracted FROM board_syncs ORDER BY started_at DESC LIMIT 2")
        for row in cursor.fetchall():
            print(f"  Sync: {row[0]} -> Extracted: {row[3]}, Inserted: {row[1]}, Updated: {row[2]}")

if __name__ == "__main__":
    asyncio.run(main())
