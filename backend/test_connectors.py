import asyncio
from src.discovery.connectors.bootstrap import bootstrap_connectors
from src.discovery.registry.connector_registry import ConnectorRegistry

async def test():
    bootstrap_connectors()
    
    # Check if connectors are registered
    print("Registered Connectors:")
    for ats in ["smartrecruiters", "rippling", "breezy", "teamtailor"]:
        connector = ConnectorRegistry.get(ats)
        print(f"  {ats}: {'Found' if connector else 'Missing'}")

if __name__ == "__main__":
    asyncio.run(test())
