import time
import logging
from src.config.settings import settings
from src.workers.worker_base import BaseWorker

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JobScoringWorker")

BATCH_SIZE = 500
# Brief pause between batches — this is pure CPU-bound scoring work (no I/O
# wait to hide behind), so a small yield keeps it from starving other
# processes on the same box rather than needing it for correctness.
BATCH_PAUSE_SECONDS = 0.25
# How long to sleep after a user has zero unscored jobs left (fully caught
# up) before checking them again — new jobs get discovered continuously.
IDLE_RECHECK_SECONDS = 300


class JobScoringWorker(BaseWorker):
    """
    Precomputes user_job_scores against the *entire* active-jobs pool
    (1M+ rows), incrementally and per-user, so the dashboard can read a
    user's best matches instantly via get_jobs_from_precomputed() instead of
    live-scoring a bounded ~2000-job recent window on every request.

    Runs continuously: for each user with a career profile, repeatedly pulls
    batches of active jobs they haven't been scored against yet (or whose
    score predates their current profile — see get_unscored_job_batch's
    anti-join), scores them with the same HardRejectFilter + IntentFilter
    pipeline the live path already used, and upserts results. A user who
    edits their profile just gets a new profile_updated_at, which makes
    every existing score for them look "stale" again and they get
    progressively rescored the same way.
    """

    def __init__(self):
        super().__init__("JobScoringWorker")
        self._last_seen_empty: dict[str, float] = {}

    def _score_user_once(self, user_id: str, profile_updated_at: str) -> int:
        repos = self.repos
        # Force a fresh profile load — the repository's cache only keys on
        # user_id, not profile_updated_at, so a mid-run profile edit
        # wouldn't otherwise be picked up until worker restart.
        cache = getattr(repos.job, "_profile_cache", None)
        if cache is not None:
            cache.pop(user_id, None)

        total_scored = 0
        while self.running:
            with repos.job.transaction() as conn:
                batch = repos.job.get_unscored_job_batch(user_id, profile_updated_at, limit=BATCH_SIZE)
                profile = repos.job._load_profile(conn, user_id)

            if not batch:
                break

            passed, rejected, _ = repos.job._hard_reject.filter_batch(batch, profile)
            scored, _ = repos.job._intent_filter.score_batch(passed, profile)
            scored_by_id = {j["job_id"]: j for j in scored}

            to_store = []
            for j in batch:
                if j["job_id"] in scored_by_id:
                    sj = scored_by_id[j["job_id"]]
                    to_store.append({
                        "job_id": j["job_id"],
                        "job_score": round(sj.get("intent_score", 0.0) * 100),
                        "intent_score": sj.get("intent_score", 0.0),
                        "passed_hard_reject": True,
                        "rejection_reason": None,
                        "score_breakdown": sj.get("score_breakdown", []),
                    })
                else:
                    rej = next((r for r in rejected if r["job_id"] == j["job_id"]), None)
                    to_store.append({
                        "job_id": j["job_id"],
                        "job_score": 0,
                        "intent_score": 0.0,
                        "passed_hard_reject": False,
                        "rejection_reason": (rej or {}).get("_rejection_reason"),
                        "score_breakdown": [],
                    })

            repos.job.store_job_scores(user_id, profile_updated_at, to_store)
            total_scored += len(to_store)
            time.sleep(BATCH_PAUSE_SECONDS)

        return total_scored

    def run(self):
        logger.info("JobScoringWorker started.")
        while self.running:
            try:
                users = self.repos.job.get_users_needing_scoring()
                processed_this_cycle = 0

                for user_id, profile_updated_at in users:
                    if not self.running:
                        break

                    last_empty = self._last_seen_empty.get(user_id)
                    if last_empty is not None and (time.time() - last_empty) < IDLE_RECHECK_SECONDS:
                        continue

                    scored = self._score_user_once(user_id, profile_updated_at)
                    processed_this_cycle += scored
                    if scored == 0:
                        self._last_seen_empty[user_id] = time.time()
                    else:
                        self._last_seen_empty.pop(user_id, None)
                        logger.info(f"Scored {scored} jobs for user_id={user_id}")

                self.heartbeat(jobs_processed=processed_this_cycle)
                if processed_this_cycle == 0:
                    time.sleep(30)
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in JobScoringWorker loop: {e}")
                self.heartbeat(failure_increment=1, last_error=str(e))
                self.check_fatal_exception(e)
                time.sleep(60)

        self.stop()
        logger.info("JobScoringWorker stopped.")


if __name__ == "__main__":
    worker = JobScoringWorker()
    worker.run()
