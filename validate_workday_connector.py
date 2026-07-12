import asyncio
import sqlite3
from src.discovery.models import Board, WorkdayBoardIdentity
from src.discovery.pipeline.sync_session import BoardSyncSession

async def main():
    db_path = "test_phase4.db"
    
    # 1. Create a mock Board object for Nvidia
    identity = WorkdayBoardIdentity(ats="workday", tenant="nvidia", site="NVIDIAExternalCareerSite")
    board = Board(
        identity=identity,
        endpoint="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        provider="workday",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    
    # 2. Run the Sync Session
    session = BoardSyncSession(board, db_path=db_path)
    print("🚀 Running BoardSyncSession for Nvidia (New Connector Architecture)...")
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
        if row:
            print(f"  ✅ Snapshot found: compression={row['compression']}, size={row['size_bytes']} bytes")
        else:
            print("  ❌ Snapshot not found!")
            
        # Check Sync Log
        row = conn.execute("SELECT * FROM board_syncs WHERE id = ?", (stats["id"],)).fetchone()
        if row:
            print(f"  ✅ Sync Log found: {row['jobs_inserted']} jobs inserted")
        else:
            print("  ❌ Sync Log not found!")
            
        # Check Jobs
        cursor = conn.execute("SELECT COUNT(*) as c FROM jobs")
        count = cursor.fetchone()['c']
        print(f"  ✅ Jobs found: {count} total jobs stored")

if __name__ == "__main__":
    asyncio.run(main())
