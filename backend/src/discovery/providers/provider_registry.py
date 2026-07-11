from typing import Dict, Type
from src.discovery.providers.base_provider import BaseProvider

class ProviderRegistry:
    """
    Factory for instantiating Discovery Providers.
    Follows the plugin architecture so new sources can be added without modifying the engine.
    """
    
    _providers: Dict[str, Type[BaseProvider]] = {}
    
    @classmethod
    def register(cls, provider_class: Type[BaseProvider]):
        """Registers a BaseProvider subclass."""
        instance = provider_class()
        cls._providers[instance.provider_name] = provider_class
        
    @classmethod
    def get_all_providers(cls) -> Dict[str, BaseProvider]:
        """Returns instantiated versions of all registered providers."""
        return {name: p_class() for name, p_class in cls._providers.items()}
