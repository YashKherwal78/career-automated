from src.system.logger import setup_logger
logger = setup_logger('connector_manager')
import concurrent.futures
from typing import List, Dict, Any
from src.discovery.connector_registry import ConnectorRegistry
from src.discovery.discovery_session import DiscoverySession

class ConnectorManager:
    """
    Orchestrates the healthy connectors supplied by the registry.
    Connectors return raw payloads, which are collected here.
    """
    def __init__(self, registry: ConnectorRegistry):
        self.registry = registry
        self.connectors = self.registry.get_healthy_connectors()

    def run_all(self, session: DiscoverySession, payload: Dict[str, Any] = None) -> List[Any]:
        """
        Runs all healthy connectors in parallel.
        Returns a list of raw payloads.
        """
        if payload is None:
            payload = {}

        raw_payloads = []
        logger.info(f"ConnectorManager: Launching {len(self.connectors)} healthy connectors in parallel...")
        
        def run_connector(connector):
            try:
                logger.info(f"ConnectorManager: Running {connector.name}...")
                results = connector.discover(session.session_id, payload)
                
                # Log metrics for this specific run
                session.log_metrics(
                    connectors_executed=1,
                    jobs_returned=len(results) if isinstance(results, list) else 1
                )
                return results
            except Exception as e:
                logger.info(f"ConnectorManager: {connector.name} failed during discover(): {e}")
                session.log_metrics(connectors_executed=1, errors=1)
                return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_connector = {executor.submit(run_connector, c): c for c in self.connectors}
            for future in concurrent.futures.as_completed(future_to_connector):
                connector = future_to_connector[future]
                try:
                    result = future.result()
                    if result:
                        if isinstance(result, list):
                            raw_payloads.extend(result)
                        else:
                            raw_payloads.append(result)
                except Exception as exc:
                    logger.info(f'{connector.name} generated an exception: {exc}')
                    
        return raw_payloads
