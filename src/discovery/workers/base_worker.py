import asyncio
import logging
from typing import Dict, Any, Type
from src.discovery.queue.base_queue import BaseQueue
from src.discovery.registry.source_registry import SourceRegistry

logger = logging.getLogger(__name__)

class BaseWorker:
    """
    Generic worker loop that continuously pulls tasks from a BaseQueue,
    finds the appropriate SourceAdapter, fetches data, parses it, and pushes
    events to the Event Bus (or pipeline queue).
    """
    
    def __init__(self, task_queue: BaseQueue, event_bus: BaseQueue):
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.is_running = False
        
    async def start(self, queue_name: str, concurrency: int = 3):
        self.is_running = True
        logger.info(f"Starting Worker Pool with concurrency {concurrency} on queue {queue_name}")
        
        tasks = [self._worker_loop(queue_name) for _ in range(concurrency)]
        await asyncio.gather(*tasks)
        
    def stop(self):
        self.is_running = False
        
    async def _worker_loop(self, queue_name: str):
        while self.is_running:
            item = self.task_queue.pop(queue_name)
            if not item:
                await asyncio.sleep(5) # No tasks, backoff
                continue
                
            item_id = item["_item_id"]
            payload = item["payload"]
            
            try:
                await self._process_task(payload)
                self.task_queue.ack(queue_name, item_id)
            except Exception as e:
                logger.error(f"Task failed: {e}")
                self.task_queue.nack(queue_name, item_id, reason=str(e))
                
    async def _process_task(self, task: Dict[str, Any]):
        url = task.get("url")
        if not url:
            raise ValueError("Task missing URL")
            
        adapter = SourceRegistry.find_adapter_for_url(url)
        if not adapter:
            raise ValueError(f"No registered SourceAdapter can handle URL: {url}")
            
        # 1. Fetch
        raw_payload = await adapter.fetch(task)
        
        # 2. Parse
        parsed_data = adapter.parse(raw_payload)
        
        # 3. Discover
        jobs = adapter.discover_jobs(parsed_data)
        
        # 4. Emit Events (JobDiscovered)
        for job in jobs:
            event = {
                "event_type": "JobDiscovered",
                "source": adapter.source_name,
                "parser_version": adapter.parser_version,
                "job_data": job,
                "company_id": task.get("company_id")
            }
            self.event_bus.push("pipeline_queue", event)
