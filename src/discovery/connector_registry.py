import yaml
from typing import Dict, Any, List
from src.discovery.discovery_connector import DiscoveryConnector

class ConnectorRegistry:
    """
    Runtime registry for all Discovery Connectors.
    Reads config, instantiates classes, and filters out unhealthy ones.
    """
    def __init__(self, config_path: str = "src/config/connectors.yaml"):
        self.config_path = config_path
        self.connectors: Dict[str, DiscoveryConnector] = {}
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Failed to load connectors config: {e}")
            self.config = {}

    def register(self, name: str, connector: DiscoveryConnector):
        """Register an instantiated connector."""
        if name in self.config and self.config[name].get('enabled', False):
            self.connectors[name] = connector

    def get_healthy_connectors(self) -> List[DiscoveryConnector]:
        healthy = []
        for name, connector in self.connectors.items():
            try:
                connector.initialize()
                if connector.health_check():
                    healthy.append(connector)
                else:
                    print(f"ConnectorRegistry: {name} failed health check. Disabling.")
            except Exception as e:
                print(f"ConnectorRegistry: {name} failed initialization: {e}")
                
        # Sort by priority defined in config
        healthy.sort(key=lambda c: self.config.get(c.name.lower().replace("connector", ""), {}).get('priority', 99))
        return healthy
