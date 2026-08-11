-- Semantic embeddings for jobs and candidate profiles (pgvector), enabling
-- cosine-similarity nearest-neighbor search across the full active-jobs
-- pool instead of a bounded recent-jobs window or full per-user table scan.

CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE public.normalized_jobs
    ADD COLUMN IF NOT EXISTS embedding vector(384);

ALTER TABLE public.user_career_profiles
    ADD COLUMN IF NOT EXISTS embedding vector(384);

-- HNSW index for fast approximate nearest-neighbor search. Built once
-- populated (an index over an all-NULL column is created empty and grows
-- as the backfill worker fills rows in) — cosine distance since embedding
-- magnitude isn't meaningful here, only direction/similarity.
CREATE INDEX IF NOT EXISTS idx_normalized_jobs_embedding_hnsw
    ON public.normalized_jobs
    USING hnsw (embedding vector_cosine_ops)
    WHERE status = 'ACTIVE';
