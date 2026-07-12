import asyncio
import sqlite3
from src.discovery.models import Board, StandardBoardIdentity
from src.discovery.pipeline.sync_session import BoardSyncSession
import src.discovery.workers.greenhouse_adapter
import src.discovery.workers.lever_adapter
import src.discovery.workers.ashby_adapter
import src.discovery.workers.workday_adapter
import src.discovery.workers.smartrecruiters_adapter

async def main():
    db_path = "test_phase2.db"
    
    # 1. Create a mock Board object
    identity = StandardBoardIdentity(ats="greenhouse", board_token="figma")
    board = Board(
        identity=identity,
        endpoint="https://boards.greenhouse.io/figma",
        provider="greenhouse",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    
    # 2. Run the Sync Session
    session = BoardSyncSession(board, db_path=db_path)
    print("🚀 Running BoardSyncSession for Figma...")
    stats = await session.execute()
    
    print("\n✅ Sync Complete. Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
        
    if not stats["success"]:
        print("❌ Sync Failed!")
        return
        
    # 3. Verify Database
    print("\n🔍 Verifying Database...")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # Check Snapshot
        row = conn.execute("SELECT * FROM board_snapshots WHERE id = ?", (stats["snapshot_id"],)).fetchone()
        print(f"  ✅ Snapshot found: compression={row['compression']}, size={row['size_bytes']} bytes")
        
        # Check Sync Log
        row = conn.execute("SELECT * FROM board_syncs WHERE id = ?", (stats["id"],)).fetchone()
        print(f"  ✅ Sync Log found: {row['jobs_inserted']} jobs inserted")
        
        # Check Jobs
        cursor = conn.execute("SELECT COUNT(*) as c FROM jobs")
        count = cursor.fetchone()['c']
        print(f"  ✅ Jobs found: {count} total jobs stored")

if __name__ == "__main__":
    asyncio.run(main())
