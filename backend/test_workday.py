import asyncio
from src.discovery.models import WorkdayBoardIdentity, Board
from src.discovery.pipeline.http_client import HttpClient
from src.discovery.connectors.workday import WorkdayConnector

async def test():
    identity = WorkdayBoardIdentity(ats="workday", tenant="3m", site="search")
    board = Board(
        company_id="workday_3m/search",
        identity=identity,
        endpoint="https://3m.wd1.myworkdayjobs.com/search",
        provider="workday",
        discovered_by="test",
        discovered_at=0.0,
        last_verified_at=0.0
    )
    async with HttpClient() as client:
        connector = WorkdayConnector()
        jobs = []
        async for result in connector.sync(board, client):
            if hasattr(result, 'status_code'):
                print("API result:", result.status_code)
            else:
                jobs.append(result)
            if len(jobs) >= 20:
                break
        print(f"Yielded {len(jobs)} jobs")
        
        # Test Normalization
        from src.discovery.pipeline.normalizers import WorkdayNormalizer
        normalizer = WorkdayNormalizer()
        canonical = []
        for rj in jobs:
            canonical.extend(normalizer.normalize(rj))
        print(f"Normalized {len(canonical)} jobs")
        if canonical:
            print("First Job Title:", canonical[0].title)
            print("First Job Apply URL:", canonical[0].apply_url)
            from src.discovery.pipeline.job_validator import JobValidator
            print("Validation Errors:", JobValidator.validate(canonical[0]))

if __name__ == "__main__":
    asyncio.run(test())
