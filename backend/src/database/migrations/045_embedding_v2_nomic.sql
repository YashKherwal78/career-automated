-- 045_embedding_v2_nomic.sql
-- Second, parallel embedding column using nomic-embed-text-v1.5 (768-dim,
-- 8192-token context vs bge-small-en-v1.5's 512 tokens -- the real fix
-- for JDs getting truncated before the model ever sees the actual
-- skills/responsibilities section). Deliberately a NEW column, not a
-- migration of the existing `embedding` column: the live dashboard reads
-- `embedding` today and must keep working unmodified throughout this
-- backfill. Once embedding_v2 is fully populated and quality-checked,
-- cutting over is a query change (order by embedding_v2 instead), not a
-- risky in-place migration.

ALTER TABLE normalized_jobs ADD COLUMN embedding_v2 vector(768);
ALTER TABLE user_career_profiles ADD COLUMN embedding_v2 vector(768);

-- HNSW index deliberately NOT here -- CREATE INDEX CONCURRENTLY can't run
-- inside MigrationRunner's transaction, applied by hand once after
-- deploy:
--   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_normalized_jobs_embedding_v2_hnsw
--     ON normalized_jobs USING hnsw (embedding_v2 vector_cosine_ops) WHERE status = 'ACTIVE';
