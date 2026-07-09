from typing import Dict, Optional, Type
from src.discovery.registry.source_adapter import SourceAdapter
from src.discovery.inspectors.base_inspector import SourceInspector, DefaultInspector

class SourceRegistry:
    """
    Central registry for ATS plugins and inspectors.
    """
    _adapters: Dict[str, SourceAdapter] = {}
    _inspectors: Dict[str, SourceInspector] = {}
    
    @classmethod
    def register(cls, adapter_class: Type[SourceAdapter]) -> None:
        """Instantiates and registers a SourceAdapter."""
        adapter_instance = adapter_class()
        cls._adapters[adapter_instance.source_name] = adapter_instance
        
    @classmethod
    def register_inspector(cls, inspector_class: Type[SourceInspector]) -> None:
        """Instantiates and registers a SourceInspector."""
        inspector_instance = inspector_class()
        cls._inspectors[inspector_instance.source_name] = inspector_instance
        
    @classmethod
    def get_adapter(cls, source_name: str) -> Optional[SourceAdapter]:
        """Returns the adapter by name, e.g., 'greenhouse'"""
        return cls._adapters.get(source_name.lower())
        
    @classmethod
    def get_inspector(cls, source_name: str) -> SourceInspector:
        """Returns the inspector by name, or a DefaultInspector if none is registered."""
        inspector = cls._inspectors.get(source_name.lower())
        if not inspector:
            return DefaultInspector(source_name.lower())
        return inspector
        
    @classmethod
    def find_adapter_for_url(cls, url: str) -> Optional[SourceAdapter]:
        """Iterates through registered adapters to find one that can handle the URL."""
        for adapter in cls._adapters.values():
            if adapter.detect(url):
                return adapter
        return None
