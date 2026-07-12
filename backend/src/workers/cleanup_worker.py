import os
import sys
import time
import sqlite3
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

                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    # 1. Clean snapshots older than 7 days
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='board_snapshots'")
                    if cursor.fetchone():
                        c_del = conn.execute("DELETE FROM board_snapshots WHERE synced_at < ?", (seven_days_ago,))
                        if c_del.rowcount > 0:
                            logger.info(f"Cleaned up {c_del.rowcount} stale snapshots.")
                            processed_count += c_del.rowcount
                    
                    # 2. Retry failed endpoints by pushing back to discovery_queue
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='career_endpoints'")
                    if cursor.fetchone():
                        # Find failed endpoints that need retry
                        cursor_f = conn.execute("SELECT company_id FROM career_endpoints WHERE status = 'FAILED' LIMIT 20")
                        failed_ids = [row[0] for row in cursor_f.fetchall()]
                        for cid in failed_ids:
                            cursor_q = conn.execute('''
                                SELECT 1 FROM local_queues 
                                WHERE queue_name = 'discovery_queue' AND json_extract(payload, '$.company_id') = ?
                            ''', (cid,))
                            if not cursor_q.fetchone():
                                self.queue.push("discovery_queue", {"company_id": cid})
                                logger.info(f"Re-enqueued failed endpoint for discovery: {cid}")
                                processed_count += 1

                    # 3. Recover stuck queue items that expired while PROCESSING
                    cursor = conn.execute('''
                        SELECT item_id, queue_name FROM local_queues
                        WHERE status = 'PROCESSING' AND locked_until <= ?
                    ''', (now,))
                    stuck_items = cursor.fetchall()
                    for row in stuck_items:
                        item_id, queue_name = row
                        conn.execute('''
                            UPDATE local_queues
                            SET status = 'QUEUED', locked_until = 0.0
                            WHERE item_id = ?
                        ''', (item_id,))
                        logger.info(f"Recovered stuck queue item {item_id} in {queue_name}")
                        processed_count += 1
                                
                    # 3. Optimize database index stats
                    conn.execute("ANALYZE")
                    logger.info("Database optimization (ANALYZE) complete.")
                    
                    # 4. Vacuum database (runs less frequently)
                    if int(now) % 3600 < 100: # once per hour roughly
                        logger.info("Running database VACUUM...")
                        conn.execute("VACUUM")

                self.heartbeat(jobs_processed=processed_count)
                time.sleep(settings.cleanup_interval)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in CleanupWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                time.sleep(60)

        self.stop()
        logger.info("CleanupWorker stopped.")

if __name__ == "__main__":
    worker = CleanupWorker()
    worker.run()
