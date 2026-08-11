-- Precomputed per-user job match scores, so the dashboard can read instantly
-- instead of live-scoring a bounded recent-jobs window on every request.
-- Populated incrementally by the background JobScoringWorker.

CREATE TABLE IF NOT EXISTS public.user_job_scores (
    user_id UUID NOT NULL,
    job_id TEXT NOT NULL,
    job_score INTEGER NOT NULL,
    intent_score DOUBLE PRECISION NOT NULL,
    passed_hard_reject BOOLEAN NOT NULL,
    rejection_reason TEXT,
    score_breakdown TEXT NOT NULL DEFAULT '[]',
    profile_updated_at TIMESTAMPTZ,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, job_id)
);

-- Dashboard's main read pattern: "give me this user's best-scoring jobs".
CREATE INDEX IF NOT EXISTS idx_user_job_scores_user_score
    ON public.user_job_scores (user_id, job_score DESC)
    WHERE passed_hard_reject = TRUE;

-- Worker's read pattern: "which active jobs haven't been scored for this
-- user yet" — anti-joined against normalized_jobs, so no index needed on
-- this side beyond the primary key already covering (user_id, job_id).
