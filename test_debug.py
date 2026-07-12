import asyncio
from src.discovery.models import Board, StandardBoardIdentity
from src.discovery.pipeline.sync_session import BoardSyncSession
import traceback

async def main():
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
    
    session_gh = BoardSyncSession(board_gh, db_path="test_phase4.db")
    try:
        stats_gh = await session_gh.execute()
        print("Figma Stats:", stats_gh)
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    import src.discovery.connectors.greenhouse
    asyncio.run(main())
