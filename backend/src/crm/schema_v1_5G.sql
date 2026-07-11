-- Company Registry Table (Single Source of Truth)
CREATE TABLE IF NOT EXISTS company_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'DISCOVERED', -- DISCOVERED, VERIFYING, ACTIVE, MONITORING, DORMANT, ARCHIVED
    ats_provider TEXT DEFAULT 'UNKNOWN',
    career_url TEXT,
    
    -- Hiring Metadata & Scoring
    pm_openings INTEGER DEFAULT 0,
    ai_openings INTEGER DEFAULT 0,
    swe_openings INTEGER DEFAULT 0,
    intern_openings INTEGER DEFAULT 0,
    is_fresh_grad_friendly BOOLEAN DEFAULT 0,
    is_remote_friendly BOOLEAN DEFAULT 0,
    is_india_hiring BOOLEAN DEFAULT 0,
    
    last_job_seen_at TEXT,
    jobs_today INTEGER DEFAULT 0,
    avg_monthly_jobs REAL DEFAULT 0.0,
    
    priority_score REAL DEFAULT 0.0,
    
    -- Confidence Metrics
    ats_confidence REAL DEFAULT 0.0,
    url_confidence REAL DEFAULT 0.0,
    
    -- Discovery Source & Auditing
    discovery_source TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TEXT,
    last_scanned_at TEXT,
    last_failed_at TEXT,
    failure_reason TEXT -- NETWORK, RATE_LIMIT, INVALID_ATS, MOVED, 404, AUTH, TIMEOUT, UNKNOWN
);

-- Capability Matrix (Which ATS supports what)
CREATE TABLE IF NOT EXISTS ats_capabilities (
    ats_provider TEXT PRIMARY KEY,
    supports_job_list BOOLEAN DEFAULT 0,
    supports_full_jd BOOLEAN DEFAULT 0,
    supports_apply_url BOOLEAN DEFAULT 0,
    supports_location BOOLEAN DEFAULT 0,
    supports_department BOOLEAN DEFAULT 0,
    supports_remote BOOLEAN DEFAULT 0,
    supports_incremental_scan BOOLEAN DEFAULT 0,
    supports_rate_limit BOOLEAN DEFAULT 0,
    confidence REAL DEFAULT 0.0,
    current_version TEXT
);

-- Discovery Events (Event Sourcing)
CREATE TABLE IF NOT EXISTS discovery_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    event_type TEXT NOT NULL, -- COMPANY_ADDED, ATS_CHANGED, NEW_JOBS_FOUND, CONNECTOR_FAILED
    event_payload TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES company_registry(id)
);
