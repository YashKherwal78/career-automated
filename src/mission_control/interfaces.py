from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ApplicationExecutorInterface(ABC):
    """
    STRICT BOUNDARY: Do NOT implement or connect this interface for Sprint 1.6.
    This explicitly isolates the Greenhouse Auto Apply Engine from the Application Strategy Queue.
    """
    
    @abstractmethod
    def submit_application(self, strategy_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submits the tailored application via Playwright."""
        pass
    
    @abstractmethod
    def drain_queue(self, queue_items: List[Dict[str, Any]]) -> None:
        """Processes the Strategy Queue."""
        pass
