-- 044_job_search_vector.sql
-- BM25-style lexical search layer, kept separate from the embedding column
-- entirely -- this is a plain, non-generated tsvector (not GENERATED
-- ALWAYS AS ... STORED) specifically so adding it doesn't force a full
-- table rewrite/lock on a live 1.4M+ row table under continuous crawler
-- writes. A trigger keeps it current for new/updated rows going forward;
-- a separate backfill script (scripts/backfill_search_vector.py) fills in
-- existing rows in batches, same pattern as the other backfill loops.
--
-- Title is weighted 'A' (highest), description 'B' -- so a title match
-- outranks a description-only match at the same term-frequency, which is
-- the right default for job search (a title that says "AI Engineer"
-- should rank above a posting that only mentions "AI" once in a long
-- description).

ALTER TABLE normalized_jobs ADD COLUMN search_vector tsvector;

CREATE OR REPLACE FUNCTION normalized_jobs_search_vector_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector :=
    setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_normalized_jobs_search_vector ON normalized_jobs;
CREATE TRIGGER trg_normalized_jobs_search_vector
  BEFORE INSERT OR UPDATE OF title, description ON normalized_jobs
  FOR EACH ROW EXECUTE FUNCTION normalized_jobs_search_vector_update();

-- The GIN index is intentionally NOT in this file. MigrationRunner
-- (src/database/migrate.py) runs every statement in a migration file
-- against the same connection with one commit at the end -- CONCURRENTLY
-- cannot run inside a transaction block, so it has to be applied by hand
-- once, outside the runner:
--   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_normalized_jobs_search_vector
--     ON normalized_jobs USING GIN(search_vector);
