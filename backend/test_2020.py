import asyncio
from src.workers.adaptive_crawler_worker import AdaptiveCrawlerWorker

async def test():
    worker = AdaptiveCrawlerWorker()
    
    # Mock reserve_due_board to return our targeted endpoint
    class MockState:
        def reserve_due_board(self, *args, **kwargs):
            if hasattr(self, 'called'):
                return None
            self.called = True
            return {
                "id": "workday_2020companies/external_careers",
                "company_id": "workday_2020companies/external_careers",
                "endpoint": "https://2020companies.wd1.myworkdayjobs.com/2020companies",
                "provider_id": "workday"
            }
            
    worker.repos.company_state = MockState()
    
    # Spy on BoardSyncSession to see what identity it gets
    from src.discovery.pipeline.sync_session import BoardSyncSession
    orig_init = BoardSyncSession.__init__
    def mock_init(self, board, *args, **kwargs):
        print(f"Board identity constructed: {board.identity}")
        print(f"Endpoint: {board.endpoint}")
        orig_init(self, board, *args, **kwargs)
    BoardSyncSession.__init__ = mock_init
    
    # Do not actually crawl 287k jobs
    async def mock_execute(self):
        print("Mock executing crawl to prevent long fetch...")
        return {"jobs_extracted": 1, "success": True}
    BoardSyncSession.execute = mock_execute
    
    # Run a single batch cycle
    await worker._crawl_batch()
    print("Done")

if __name__ == "__main__":
    asyncio.run(test())
