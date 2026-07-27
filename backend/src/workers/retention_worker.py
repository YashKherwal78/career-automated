import asyncio
import time
import logging
from src.api.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RetentionWorker")

class RetentionWorker:
    """
    Background worker to clean up expired evidence payloads.
    PostgreSQL autovacuum handles the storage reclamation asynchronously.
    """
    def __init__(self, check_interval_seconds: int = 86400):
        self.check_interval_seconds = check_interval_seconds
        
    async def run(self):
        logger.info(f"RetentionWorker starting. Check interval: {self.check_interval_seconds}s")
        while True:
            try:
                self.cleanup_expired_evidence()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                
            await asyncio.sleep(self.check_interval_seconds)

    def cleanup_expired_evidence(self):
        now = time.time()
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM crawl_evidence WHERE evidence_category != 'REFERENCE' AND expires_at > 0 AND expires_at < ?", 
                (now,)
            )
            deleted = cursor.rowcount
            conn.commit()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired evidence records.")

if __name__ == "__main__":
    worker = RetentionWorker(check_interval_seconds=3600)
    asyncio.run(worker.run())
