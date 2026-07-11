-- Drop the old normalized_jobs and recreate it with the full Lifecycle and Content Hashing
DROP TABLE IF EXISTS normalized_jobs;

CREATE TABLE normalized_jobs (
    fingerprint TEXT PRIMARY KEY, -- SHA256(company + title + location + employment + ATS ID)
    content_hash TEXT NOT NULL,   -- SHA256(title + description + requirements + location + employment)
    
    company_id TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    employment_type TEXT,
    remote BOOLEAN,
    department TEXT,
    description TEXT,
    apply_url TEXT,
    connector TEXT,
    ats_id TEXT,
    
    -- Lifecycle
    status TEXT DEFAULT 'NEW', -- NEW, ACTIVE, UPDATED, CLOSED, ARCHIVED
    discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- JIE Version Tracking
    jie_version TEXT,
    parsed_at TEXT,
    
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);
