import asyncio
from typing import Callable, Dict, Any, List

class InMemoryEventBus:
    """
    A lightweight, pragmatic in-memory event bus for local development and single-machine scaling.
    Replaces the need for RabbitMQ/Kafka during early production.
    """
    
    def __init__(self):
        # Maps event_type -> List of async callback functions
        self.listeners: Dict[str, List[Callable]] = {}
        
    def subscribe(self, event_type: str, callback: Callable):
        """Registers a listener for a specific event type."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        
    async def publish(self, event_type: str, payload: Dict[str, Any]):
        """Emits an event to all registered listeners asynchronously."""
        if event_type in self.listeners:
            tasks = []
            for callback in self.listeners[event_type]:
                # Wrap the callback execution in a task so they run concurrently 
                # and don't block the publisher.
                tasks.append(asyncio.create_task(self._safe_execute(callback, payload)))
            
            if tasks:
                # We don't await the tasks here to fire-and-forget, keeping publishing fast.
                # The asyncio event loop will handle their execution.
                pass 
                
    async def _safe_execute(self, callback: Callable, payload: Dict[str, Any]):
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(payload)
            else:
                callback(payload)
        except Exception as e:
            # In a production system, this would route to a Dead Letter Queue (DLQ)
            print(f"[EventBus] Error in listener {callback.__name__}: {e}")

# Global instance for single-machine deployments
event_bus = InMemoryEventBus()
