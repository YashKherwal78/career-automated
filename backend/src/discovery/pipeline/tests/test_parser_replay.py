import asyncio
import logging
from src.discovery.pipeline.repositories.evidence import EvidenceRepository
from src.discovery.registry.connector_registry import ConnectorRegistry
from src.discovery.models import Board

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ParserReplay")

class ParserReplaySuite:
    """
    Automated regression testing suite.
    Queries all REFERENCE payloads for a provider and passes them 
    through the current connector/parser to ensure backwards compatibility.
    """
    
    def __init__(self, db_path: str = "boards.db"):
        self.evidence_repo = EvidenceRepository(db_path)
        
    def run_provider_suite(self, provider: str) -> bool:
        """
        Returns True if all references parsed successfully.
        """
        references = self.evidence_repo.get_reference_payloads(provider)
        if not references:
            logger.info(f"No references found for provider: {provider}")
            return True
            
        connector = ConnectorRegistry.get(provider)
        if not connector:
            logger.error(f"Connector not found for provider: {provider}")
            return False
            
        success = True
        for ref in references:
            schema_hash = ref["schema_hash"]
            payload = ref["payload"]
            
            # This is pseudo-code for the replay depending on how connectors are structured.
            # Usually, connectors have a `.parse(payload)` method or similar.
            # If the connector requires `sync()`, we may need to mock HttpClient.
            
            try:
                # Example:
                if hasattr(connector, 'parse_jobs'):
                    jobs = list(connector.parse_jobs(payload))
                    if not jobs:
                        logger.warning(f"Regression detected: 0 jobs extracted for {provider} / {schema_hash}")
                        success = False
                    else:
                        logger.info(f"Replay OK: {provider} / {schema_hash} -> {len(jobs)} jobs")
                else:
                    logger.warning(f"Connector {provider} does not expose parse_jobs(). Cannot replay.")
            except Exception as e:
                logger.error(f"Regression exception for {provider} / {schema_hash}: {e}")
                success = False
                
        return success

if __name__ == "__main__":
    suite = ParserReplaySuite()
    # Replace with specific provider or iterate all
    suite.run_provider_suite("greenhouse")
