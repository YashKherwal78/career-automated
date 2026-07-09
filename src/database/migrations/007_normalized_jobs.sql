-- 007_normalized_jobs.sql
-- Create the normalized_jobs table that JobRepository writes to.
--
-- Previously this table only existed in src/crm/schema_v1.sql which was never
-- applied by MigrationRunner. That caused the table to be absent on a clean clone,
-- silently breaking the job crawling stage of Pipeline A.
--
-- Columns match exactly what src/discovery/pipeline/repositories/job.py inserts.

CREATE TABLE IF NOT EXISTS normalized_jobs (
    job_id              TEXT    PRIMARY KEY,
    provider_job_id     TEXT,
    company_id          TEXT    NOT NULL,
    provider            TEXT    NOT NULL,
    title               TEXT,
    location            TEXT,
    remote_type         TEXT,
    employment_type     TEXT,
    department          TEXT,
    salary_min          REAL,
    salary_max          REAL,
    currency            TEXT,
    posted_at           TEXT,
    apply_url           TEXT,
    description         TEXT,
    job_hash            TEXT,
    status              TEXT    NOT NULL DEFAULT 'ACTIVE',
    raw_payload_json    TEXT,
    closed_at           TEXT,
    normalized_at       REAL    DEFAULT (unixepoch('now'))
);

CREATE INDEX IF NOT EXISTS idx_normalized_jobs_company_status
    ON normalized_jobs (company_id, status);

CREATE INDEX IF NOT EXISTS idx_normalized_jobs_hash
    ON normalized_jobs (job_hash);
