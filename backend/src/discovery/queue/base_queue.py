from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseQueue(ABC):
    """
    Abstract interface for queues to allow swapping SQLite for Redis/SQS in production.
    """
    
    @abstractmethod
    def push(self, queue_name: str, payload: Dict[str, Any]) -> str:
        """Pushes an item onto the queue. Returns item ID."""
        pass
        
    @abstractmethod
    def pop(self, queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Pops an item from the queue, establishing a lock/lease."""
        pass
        
    @abstractmethod
    def ack(self, queue_name: str, item_id: str) -> bool:
        """Acknowledges successful processing, removing the item from the queue."""
        pass
        
    @abstractmethod
    def nack(self, queue_name: str, item_id: str, reason: str = "", backoff_seconds: int = 3600) -> bool:
        """Negative acknowledgment. Returns the item to the queue or pushes to a DLQ/Retry Queue."""
        pass
