import os
import sys
import time
import asyncio
import logging
from src.workers.worker_base import BaseWorker
from src.core.repositories.manager import RepositoryManager
from src.config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OutboxPublisher")

class OutboxPublisherWorker(BaseWorker):
    def __init__(self):
        super().__init__("OutboxPublisherWorker")
        self.repos = RepositoryManager(self.db_path)

    async def run_async(self):
        logger.info(f"OutboxPublisherWorker starting as {self.worker_id}")
        while self.running:
            try:
                # 1. Claim pending events
                events = self.repos.outbox.claim_pending_events(batch_size=50)
                
                if not events:
                    # No events, sleep
                    self.heartbeat()
                    await asyncio.sleep(5)
                    continue

                for event in events:
                    try:
                        # V1 implementation: Publish directly to logs/stdout (simulate event bus)
                        logger.info(f"--- EVENT PUBLISHED ---")
                        logger.info(f"ID: {event['event_id']}")
                        logger.info(f"Type: {event['event_type']}")
                        logger.info(f"Aggregate: {event['aggregate_type']} (ID: {event['aggregate_id']})")
                        logger.info(f"Payload: {event['payload']}")
                        logger.info(f"-----------------------")
                        
                        # Mark as delivered
                        self.repos.outbox.mark_delivered(event['event_id'])
                    except Exception as ex:
                        logger.error(f"Failed to publish event {event['event_id']}: {ex}")
                        self.repos.outbox.mark_failed(event['event_id'], str(ex))

                # Prune delivered events older than 30 days
                pruned = self.repos.outbox.prune_delivered_events(days_old=30)
                if pruned > 0:
                    logger.info(f"Pruned {pruned} delivered outbox events older than 30 days.")

                self.heartbeat(jobs_processed=len(events))
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error in OutboxPublisherWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                await asyncio.sleep(10)

if __name__ == "__main__":
    worker = OutboxPublisherWorker()
    asyncio.run(worker.run_async())
