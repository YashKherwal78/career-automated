from typing import Optional, Any, Dict
from src.core.repositories.interfaces import IConnectorRepository
from src.discovery.registry.connector_registry import ConnectorRegistry

class ConnectorRepository(IConnectorRepository):
    def get_connector(self, provider: str, tx: Optional[Any] = None) -> Optional[Dict[str, Any]]:
        connector = ConnectorRegistry.get(provider)
        if connector:
            return {
                "id": provider,
                "version": getattr(connector, 'VERSION', '1.0'),
                "health": "Healthy",
                "enabled": True,
                "instance": connector
            }
        return None
