-- Rename the old table to the archive table
ALTER TABLE raw_jobs RENAME TO raw_payload_archive;

-- Create the canonical job store
CREATE TABLE IF NOT EXISTS canonical_job_store (
    fingerprint TEXT PRIMARY KEY,
    payload_archive_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    provider TEXT,
    normalized_title TEXT,
    normalized_location TEXT,
    normalized_employment_type TEXT,
    source_trust_score INTEGER DEFAULT 50,
    payload_quality_score INTEGER DEFAULT 0,
    canonicalized_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id),
    FOREIGN KEY(payload_archive_id) REFERENCES raw_payload_archive(fingerprint)
);

-- Update job_states foreign keys
-- Note: SQLite doesn't easily let you alter foreign keys without recreating the table, 
-- but since job_states was just created and is likely empty, we can drop and recreate it.
DROP TABLE IF EXISTS job_states;

CREATE TABLE job_states (
    fingerprint TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    status TEXT DEFAULT 'DISCOVERED',
    intent_score INTEGER,
    match_score INTEGER,
    company_score INTEGER,
    priority_score INTEGER,
    feature_vector_json TEXT,
    rejection_reason TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fingerprint) REFERENCES canonical_job_store(fingerprint),
    FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);
