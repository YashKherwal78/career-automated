from typing import Dict, Type
from src.discovery.registry.connector import Connector

class ConnectorRegistry:
    _registry: Dict[str, Type[Connector]] = {}

    @classmethod
    def register(cls, provider: str, connector_class: Type[Connector]):
        cls._registry[provider] = connector_class

    @classmethod
    def get(cls, provider: str) -> Connector | None:
        connector_class = cls._registry.get(provider)
        if connector_class:
            return connector_class()
        return None
