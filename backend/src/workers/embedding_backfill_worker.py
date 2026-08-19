import time
import logging
from src.workers.worker_base import BaseWorker
from src.discovery.embeddings import embed_batch, job_embedding_text
from src.discovery.jie.extractor import JDExtractor, JIE_VERSION

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

    Also runs JDExtractor once per job here (structured technologies/
    skills/responsibilities feed both a better embedding -- see
    job_embedding_text's docstring -- and get cached to normalized_jobs.
    jd_profile, a column that existed in the schema but nothing ever
    wrote to before this). experience_min/experience_max are persisted
    the same way so job search can filter on experience directly via SQL
    instead of re-running JDExtractor per request.
    """

    def __init__(self):
        super().__init__("EmbeddingBackfillWorker")
        self._extractor = JDExtractor()

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

                texts = []
                job_id_to_profile = {}
                for j in batch:
                    structured = None
                    try:
                        structured = self._extractor.extract(title=j["title"] or "", jd_text=j["description"] or "")
                    except Exception as e:
                        logger.warning(f"JDExtractor failed for job_id={j['job_id']}: {e}")

                    if structured:
                        texts.append(job_embedding_text(
                            j["title"], j["description"],
                            technologies=structured.technologies,
                            skills=structured.skills,
                            responsibilities=structured.responsibilities,
                            experience_min=structured.experience_min,
                            experience_max=structured.experience_max,
                        ))
                        job_id_to_profile[j["job_id"]] = (
                            structured.model_dump_json(), structured.jd_hash, JIE_VERSION,
                            structured.experience_min, structured.experience_max,
                        )
                    else:
                        texts.append(job_embedding_text(j["title"], j["description"]))

                vectors = embed_batch(texts)

                job_id_to_vector = {j["job_id"]: v for j, v in zip(batch, vectors)}
                self.repos.job.store_job_embeddings(job_id_to_vector, job_id_to_profile)

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
