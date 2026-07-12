import asyncio
from src.discovery.models import Board, StandardBoardIdentity
from src.discovery.pipeline.sync_session import BoardSyncSession
from src.discovery.pipeline.http_client import HttpClient
import src.discovery.connectors.greenhouse

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
    
    async with HttpClient() as client:
        connector = src.discovery.connectors.greenhouse.GreenhouseConnector()
        async for item in connector.sync(board_gh, client):
            print(type(item))

if __name__ == "__main__":
    asyncio.run(main())
