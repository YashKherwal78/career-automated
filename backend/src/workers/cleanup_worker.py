import os
import sys
import time
import logging
from src.config.settings import settings
from src.workers.worker_base import BaseWorker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CleanupWorker")

class CleanupWorker(BaseWorker):
    def __init__(self):
        super().__init__("CleanupWorker")

    def run(self):
        logger.info("CleanupWorker started.")
        while self.running:
            try:
                processed_count = 0
                now = time.time()
                seven_days_ago = now - 7 * 24 * 3600

                # 1. Clean snapshots older than 7 days
                cleaned = self.repos.cleanup.clean_old_snapshots(seven_days_ago)
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} old board snapshots.")
                    processed_count += cleaned
                
                # 2. Retry failed endpoints by pushing back to discovery_queue
                failed_ids = self.repos.cleanup.get_failed_endpoints()
                for cid in failed_ids:
                    if not self.repos.cleanup.is_in_discovery_queue(cid):
                        self.queue.push("discovery_queue", {"company_id": cid})
                        logger.info(f"Re-enqueued failed endpoint for discovery: {cid}")
                        processed_count += 1

                # 3. Recover stuck queue items that expired while PROCESSING
                recovered = self.repos.cleanup.recover_stuck_queues(now)
                if recovered > 0:
                    logger.info(f"Recovered {recovered} stuck queue items.")
                    processed_count += recovered
                            
                # 4. Optimize database index stats
                should_vacuum = (int(now) % 3600 < 100)
                self.repos.cleanup.optimize_database(should_vacuum)

                self.heartbeat(jobs_processed=processed_count)
                time.sleep(settings.cleanup_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in CleanupWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                self.check_fatal_exception(e)
                time.sleep(60)

        self.stop()
        logger.info("CleanupWorker stopped.")

if __name__ == "__main__":
    worker = CleanupWorker()
    worker.run()
