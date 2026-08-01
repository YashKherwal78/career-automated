import asyncio
import time
from src.discovery.models import WorkdayBoardIdentity, Board
from src.discovery.pipeline.sync_session import BoardSyncSession
from src.discovery.connectors.bootstrap import bootstrap_connectors

async def test():
    bootstrap_connectors()
    identity = WorkdayBoardIdentity(ats="workday", tenant="3m", site="search")
    board = Board(
        company_id="workday_3m/search",
        identity=identity,
        endpoint="https://3m.wd1.myworkdayjobs.com/search",
        provider="workday",
        discovered_by="AdaptiveCrawlerWorker",
        discovered_at=time.time(),
        last_verified_at=time.time()
    )
    
    # Monkeypatch workday connector to only return 5 raw jobs
    from src.discovery.connectors.workday import WorkdayConnector
    orig_sync = WorkdayConnector.sync
    async def mocked_sync(self, board, http_client):
        count = 0
        async for r in orig_sync(self, board, http_client):
            if not hasattr(r, 'status_code'):
                count += 1
            yield r
            if count >= 5:
                break
    WorkdayConnector.sync = mocked_sync

    print("Starting BoardSyncSession...")
    session = BoardSyncSession(board, db_path="data/crm.db")
    stats = await session.execute()
    print("Stats:", stats)

if __name__ == "__main__":
    asyncio.run(test())
