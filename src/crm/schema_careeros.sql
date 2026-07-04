-- Users & Profiles
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    active_profile TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    profile_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    profile_name TEXT NOT NULL,
    config_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resume_variants (
    variant_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    variant_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Contacts (For Sprint 1.6C)
CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    company_id TEXT REFERENCES company_identities(company_id),
    name TEXT,
    role TEXT,
    email TEXT,
    linkedin_url TEXT,
    confidence REAL,
    source TEXT,
    last_contacted_at TEXT,
    reply_status TEXT DEFAULT 'NONE',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Applications tracking
CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES normalized_jobs(job_id),
    user_id TEXT REFERENCES users(user_id),
    resume_variant_id TEXT REFERENCES resume_variants(variant_id),
    status TEXT DEFAULT 'APPLIED', -- APPLIED, INTERVIEW, OA, REJECTED, OFFER, GHOSTED
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- System Tracking
CREATE TABLE IF NOT EXISTS activities (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daemon_runs (
    run_id TEXT PRIMARY KEY,
    daemon_name TEXT NOT NULL,
    status TEXT NOT NULL, -- RUNNING, COMPLETED, FAILED
    metrics_json TEXT,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);
