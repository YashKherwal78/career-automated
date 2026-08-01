-- 008_job_intelligence_columns.sql
-- Add canonical JD intelligence columns to normalized_jobs table.
-- Eliminates separate VM caches by co-locating parsed job intelligence directly inside the jobs table.

ALTER TABLE normalized_jobs ADD COLUMN description_markdown TEXT;
ALTER TABLE normalized_jobs ADD COLUMN jd_profile TEXT;  -- JSON representation of StructuredJobProfile
ALTER TABLE normalized_jobs ADD COLUMN jd_hash TEXT;
ALTER TABLE normalized_jobs ADD COLUMN jd_version INTEGER DEFAULT 2;
ALTER TABLE normalized_jobs ADD COLUMN jd_parsed_at REAL;
ALTER TABLE normalized_jobs ADD COLUMN jd_parser TEXT DEFAULT 'jie-parser-v2';

CREATE INDEX IF NOT EXISTS idx_normalized_jobs_jd_hash ON normalized_jobs(jd_hash);
