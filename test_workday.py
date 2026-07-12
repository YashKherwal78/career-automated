import asyncio
import sqlite3
from src.discovery.models import Board, WorkdayBoardIdentity
from src.discovery.pipeline.sync_session import BoardSyncSession

# Monkeypatch WorkdayConnector to limit pagination
from src.discovery.connectors.workday import WorkdayConnector
old_sync = WorkdayConnector.sync
async def mock_sync(self, board, http_client):
    count = 0
    async for job in old_sync(self, board, http_client):
        yield job
        count += 1
        if count >= 40: # Max 2 pages
            break
WorkdayConnector.sync = mock_sync

async def main():
    db_path = "test_phase4.db"
    
    identity = WorkdayBoardIdentity(ats="workday", tenant="target", site="TargetCareers")
    board = Board(
        identity=identity,
        endpoint="https://target.wd5.myworkdayjobs.com/TargetCareers",
        provider="workday",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    
    session = BoardSyncSession(board, db_path=db_path)
    print("🚀 Running BoardSyncSession for Target (New Connector Architecture)...")
    stats = await session.execute()
    
    print("\n✅ Sync Complete. Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(main())
