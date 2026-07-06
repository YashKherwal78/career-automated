import asyncio
import logging
import sqlite3
import time
from typing import Dict, Any

from src.discovery.queue.base_queue import BaseQueue
from src.discovery.queue.event_bus import event_bus

logger = logging.getLogger(__name__)

class Scheduler:
    """
    The orchestrator that continuously polls the Company Registry for due crawls
    and dispatches them to the persistent Task Queue.
    """
    
    def __init__(self, db_path: str, task_queue: BaseQueue):
        self.db_path = db_path
        self.task_queue = task_queue
        self.is_running = False
        
    async def start(self, poll_interval: int = 60):
        self.is_running = True
        logger.info("Starting Scheduler...")
        
        while self.is_running:
            try:
                await self._dispatch_due_companies()
            except Exception as e:
                logger.error(f"Scheduler dispatch error: {e}")
                
            await asyncio.sleep(poll_interval)
            
    def stop(self):
        self.is_running = False
        
    async def _dispatch_due_companies(self):
        now = int(time.time())
        dispatched_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            # Note: Requires company_crawl_queue table to exist
            try:
                # Find companies that are due for a check and aren't currently running
                cursor = conn.execute('''
                    SELECT company_id, ats_provider, career_url 
                    FROM company_crawl_queue
                    WHERE next_check <= ? AND crawl_status != 'RUNNING'
                    LIMIT 50
                ''', (now,))
                
                due_companies = cursor.fetchall()
                
                for row in due_companies:
                    company_id, ats_provider, career_url = row
                    
                    # Create the task payload
                    task_payload = {
                        "company_id": company_id,
                        "provider": ats_provider,
                        "url": career_url,
                        "dispatched_at": now
                    }
                    
                    # Push to the worker queue
                    self.task_queue.push("crawl_tasks", task_payload)
                    
                    # Mark as running so it isn't dispatched again
                    conn.execute('''
                        UPDATE company_crawl_queue 
                        SET crawl_status = 'RUNNING' 
                        WHERE company_id = ?
                    ''', (company_id,))
                    
                    dispatched_count += 1
                    
                if dispatched_count > 0:
                    logger.info(f"Dispatched {dispatched_count} companies to Task Queue.")
                    
            except sqlite3.OperationalError as e:
                # The table might not exist yet if migration hasn't run
                logger.warning(f"Failed to query company_crawl_queue: {e}")
