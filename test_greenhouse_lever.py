import asyncio
import sqlite3
from src.discovery.models import Board, StandardBoardIdentity
from src.discovery.pipeline.sync_session import BoardSyncSession
from src.discovery.registry.connector_registry import ConnectorRegistry

async def main():
    db_path = "test_phase4.db"
    
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
    
    print("\n🚀 Running BoardSyncSession for Figma (Greenhouse Connector)...")
    session_gh = BoardSyncSession(board_gh, db_path=db_path)
    stats_gh = await session_gh.execute()
    print("✅ Sync Complete. Jobs Extracted:", stats_gh["jobs_extracted"], "Snapshot:", stats_gh["snapshot_id"])
    
    identity_lv = StandardBoardIdentity(ats="lever", board_token="netflix")
    board_lv = Board(
        identity=identity_lv,
        endpoint="https://jobs.lever.co/netflix",
        provider="lever",
        discovered_by="manual",
        discovered_at=0.0,
        last_verified_at=0.0,
        metadata={}
    )
    
    print("\n🚀 Running BoardSyncSession for Netflix (Lever Connector)...")
    session_lv = BoardSyncSession(board_lv, db_path=db_path)
    stats_lv = await session_lv.execute()
    print("✅ Sync Complete. Jobs Extracted:", stats_lv["jobs_extracted"], "Snapshot:", stats_lv["snapshot_id"])

if __name__ == "__main__":
    import src.discovery.connectors.greenhouse
    import src.discovery.connectors.lever
    
    asyncio.run(main())
