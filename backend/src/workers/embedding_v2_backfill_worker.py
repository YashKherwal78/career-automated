import time
import json
import logging
from src.workers.worker_base import BaseWorker
from src.discovery.embeddings import embed_batch_v2_documents, job_embedding_text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EmbeddingV2BackfillWorker")

BATCH_SIZE = 32  # nomic-embed-text-v1.5 is heavier per-item than bge-small; smaller batches keep memory/latency reasonable
IDLE_SLEEP_SECONDS = 60
# The 2026-08-20 outage traced back to this worker running batch after
# batch with zero pause between them, pinning 60-85% CPU continuously on a
# shared 4-vCPU production box until the box couldn't keep up with
# anything else (SSH included). This has no effect on total throughput
# that matters -- backfilling 1M+ rows takes hours regardless -- but caps
# sustained CPU so the live app always gets a slice.
BATCH_PACING_SECONDS = 2


class EmbeddingV2BackfillWorker(BaseWorker):
    """
    Parallel to EmbeddingBackfillWorker, targeting embedding_v2
    (nomic-embed-text-v1.5, migration 045) instead of the live `embedding`
    column (bge-small-en-v1.5). Deliberately separate: the live dashboard
    reads `embedding` and must keep working unmodified throughout this
    backfill -- this worker only ever writes embedding_v2, never touches
    `embedding`, jd_profile, or experience_min/max.

    If jd_profile is already populated for a job (from the v1 worker),
    reuses its structured technologies/skills/responsibilities/experience
    fields for a richer job_embedding_text the same way v1 does -- free
    reuse, no re-extraction. Falls back to plain title+description when
    jd_profile isn't there yet (most jobs, until that backfill catches
    up), which nomic-embed's 8192-token context handles fine on its own
    without the front-loading trick bge-small needed.
    """

    def __init__(self):
        super().__init__("EmbeddingV2BackfillWorker")

    def _build_text(self, job: dict) -> str:
        jd_profile_raw = job.get("jd_profile")
        if jd_profile_raw:
            try:
                structured = json.loads(jd_profile_raw)
                return job_embedding_text(
                    job["title"], job["description"],
                    technologies=structured.get("technologies"),
                    skills=structured.get("skills"),
                    responsibilities=structured.get("responsibilities"),
                    experience_min=structured.get("experience_min"),
                    experience_max=structured.get("experience_max"),
                )
            except Exception:
                pass
        return job_embedding_text(job["title"], job["description"])

    def run(self):
        logger.info("EmbeddingV2BackfillWorker started.")
        total_embedded = 0
        while self.running:
            try:
                batch = self.repos.job.get_jobs_missing_embedding_v2(limit=BATCH_SIZE)
                if not batch:
                    self.heartbeat(jobs_processed=0)
                    time.sleep(IDLE_SLEEP_SECONDS)
                    continue

                texts = [self._build_text(j) for j in batch]
                vectors = embed_batch_v2_documents(texts)
                job_id_to_vector = {j["job_id"]: v for j, v in zip(batch, vectors)}
                self.repos.job.store_job_embeddings_v2(job_id_to_vector)

                total_embedded += len(batch)
                self.heartbeat(jobs_processed=len(batch))
                if total_embedded % (BATCH_SIZE * 100) < BATCH_SIZE:
                    logger.info(f"Embedded (v2) {total_embedded} jobs so far this run.")

                time.sleep(BATCH_PACING_SECONDS)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in EmbeddingV2BackfillWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                self.check_fatal_exception(e)
                time.sleep(30)

        self.stop()
        logger.info(f"EmbeddingV2BackfillWorker stopped. Total embedded this run: {total_embedded}")


if __name__ == "__main__":
    worker = EmbeddingV2BackfillWorker()
    worker.run()
