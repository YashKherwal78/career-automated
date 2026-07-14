from typing import Dict, List, Type
from src.discovery.registry.connector import Connector

class StrategyRegistration:
    def __init__(self, priority: int, strategy: str, connector_class: Type[Connector]):
        self.priority = priority
        self.strategy = strategy
        self.connector_class = connector_class

class ConnectorRegistry:
    # provider_id -> List of registered strategies
    _registry: Dict[str, List[StrategyRegistration]] = {}

    @classmethod
    def register(cls, provider: str, strategy: str, priority: int, connector_class: Type[Connector]):
        if provider not in cls._registry:
            cls._registry[provider] = []
        
        cls._registry[provider].append(StrategyRegistration(
            priority=priority,
            strategy=strategy,
            connector_class=connector_class
        ))
        
        # Sort so highest priority is always first
        cls._registry[provider].sort(key=lambda x: x.priority, reverse=True)

    @classmethod
    def get(cls, provider: str) -> Connector | None:
        """Returns the highest priority connector instance for the provider."""
        registrations = cls._registry.get(provider)
        if registrations and len(registrations) > 0:
            # For now, we simply take the highest priority strategy.
            # In the future, this can check health metrics before returning.
            return registrations[0].connector_class()
        return None
        
    @classmethod
    def get_all_strategies(cls, provider: str) -> List[StrategyRegistration]:
        return cls._registry.get(provider, [])

    @classmethod
    def filter_by_capability(cls, **kwargs) -> List[Type[Connector]]:
        """
        Returns a list of connector classes that match all specified capability flags.
        Example: ConnectorRegistry.filter_by_capability(supports_bulk_fetch=True, requires_browser=False)
        """
        matching_connectors = []
        for provider, strategies in cls._registry.items():
            for strategy_reg in strategies:
                connector = strategy_reg.connector_class()
                caps = connector.capabilities()
                
                matches_all = True
                for flag, expected_val in kwargs.items():
                    if getattr(caps, flag, None) != expected_val:
                        matches_all = False
                        break
                        
                if matches_all:
                    matching_connectors.append(strategy_reg.connector_class)
                    
        return matching_connectors
