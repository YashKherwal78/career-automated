-- 043_normalized_jobs_experience.sql
-- Persisted experience requirement so job search/matching can filter on it
-- directly (SQL WHERE), instead of running JDExtractor at request time.
-- NULL means "not yet extracted" or "extractor found no explicit number in
-- the JD text" -- both are common (JDExtractor has weak recall on this
-- field, confirmed against real postings) and are NOT the same as
-- "0 years required", so callers must treat NULL as unknown, not junior.

ALTER TABLE normalized_jobs ADD COLUMN experience_min INTEGER;
ALTER TABLE normalized_jobs ADD COLUMN experience_max INTEGER;

CREATE INDEX IF NOT EXISTS idx_normalized_jobs_experience_min ON normalized_jobs(experience_min) WHERE status = 'ACTIVE';
