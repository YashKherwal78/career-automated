-- backend/src/database/migrations/041_ingested_job_leads.sql
CREATE TABLE IF NOT EXISTS ingested_job_leads (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    apply_link TEXT NOT NULL,
    source TEXT NOT NULL,
    source_ref TEXT,
    connector TEXT,
    jd_source TEXT,
    result_status TEXT,
    really_submitted INTEGER DEFAULT 0,
    execution_run_id TEXT,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ingested_job_leads_user_company_role
    ON ingested_job_leads (user_id, company, role);
