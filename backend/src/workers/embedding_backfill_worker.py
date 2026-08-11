import time
import logging
from src.workers.worker_base import BaseWorker
from src.discovery.embeddings import embed_batch, job_embedding_text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EmbeddingBackfillWorker")

BATCH_SIZE = 64
IDLE_SLEEP_SECONDS = 60


class EmbeddingBackfillWorker(BaseWorker):
    """
    One-time (well — ongoing, since new jobs keep arriving) backfill:
    computes and stores a semantic embedding for every active job that
    doesn't have one yet, so get_jobs_by_vector_similarity() can search
    the full pool via pgvector instead of a bounded recent-jobs window.
    """

    def __init__(self):
        super().__init__("EmbeddingBackfillWorker")

    def run(self):
        logger.info("EmbeddingBackfillWorker started.")
        total_embedded = 0
        while self.running:
            try:
                batch = self.repos.job.get_jobs_missing_embedding(limit=BATCH_SIZE)
                if not batch:
                    self.heartbeat(jobs_processed=0)
                    time.sleep(IDLE_SLEEP_SECONDS)
                    continue

                texts = [job_embedding_text(j["title"], j["description"]) for j in batch]
                vectors = embed_batch(texts)

                job_id_to_vector = {j["job_id"]: v for j, v in zip(batch, vectors)}
                self.repos.job.store_job_embeddings(job_id_to_vector)

                total_embedded += len(batch)
                self.heartbeat(jobs_processed=len(batch))
                if total_embedded % (BATCH_SIZE * 50) < BATCH_SIZE:
                    logger.info(f"Embedded {total_embedded} jobs so far this run.")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in EmbeddingBackfillWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                self.check_fatal_exception(e)
                time.sleep(30)

        self.stop()
        logger.info(f"EmbeddingBackfillWorker stopped. Total embedded this run: {total_embedded}")


if __name__ == "__main__":
    worker = EmbeddingBackfillWorker()
    worker.run()
