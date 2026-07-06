from typing import Dict, Optional, Type
from src.discovery.registry.source_adapter import SourceAdapter

class SourceRegistry:
    """
    Central registry for ATS plugins.
    """
    _adapters: Dict[str, SourceAdapter] = {}
    
    @classmethod
    def register(cls, adapter_class: Type[SourceAdapter]) -> None:
        """Instantiates and registers a SourceAdapter."""
        adapter_instance = adapter_class()
        cls._adapters[adapter_instance.source_name] = adapter_instance
        
    @classmethod
    def get_adapter(cls, source_name: str) -> Optional[SourceAdapter]:
        """Returns the adapter by name, e.g., 'greenhouse'"""
        return cls._adapters.get(source_name.lower())
        
    @classmethod
    def find_adapter_for_url(cls, url: str) -> Optional[SourceAdapter]:
        """Iterates through registered adapters to find one that can handle the URL."""
        for adapter in cls._adapters.values():
            if adapter.detect(url):
                return adapter
        return None
