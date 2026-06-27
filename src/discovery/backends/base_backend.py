from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseBackend(ABC):
    """
    Abstract interface for all discovery backends.
    Handles HTTP/Apify/SERP API execution purely as a transport layer.
    """
    
    @abstractmethod
    def fetch(self, query: str, location: str, **kwargs) -> Dict[str, Any]:
        """
        Executes a search query and returns the raw response dictionary.
        This must be completely agnostic to Job or Company domain objects.
        """
        pass
