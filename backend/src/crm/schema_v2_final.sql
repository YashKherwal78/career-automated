-- Core Company Identity Layer
CREATE TABLE IF NOT EXISTS company_identities (
    company_id TEXT PRIMARY KEY, -- UUID
    domain TEXT UNIQUE NOT NULL, -- Permanent root identity (e.g., openai.com)
    canonical_name TEXT NOT NULL,
    legal_name TEXT,
    website TEXT,
    linkedin_url TEXT,
    founders TEXT, -- JSON Array
    investors TEXT, -- JSON Array (Knowledge Graph: YC, Peak XV, etc.)
    aliases TEXT, -- JSON Array
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Decoupled Hiring Snapshots (Time-Series Data)
CREATE TABLE IF NOT EXISTS hiring_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    snapshot_date TEXT DEFAULT CURRENT_TIMESTAMP,
    pm_jobs INTEGER DEFAULT 0,
    ai_jobs INTEGER DEFAULT 0,
    swe_jobs INTEGER DEFAULT 0,
    intern_jobs INTEGER DEFAULT 0,
    remote_jobs INTEGER DEFAULT 0,
    hiring_velocity REAL DEFAULT 0.0,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);

-- Connector Performance Metrics
CREATE TABLE IF NOT EXISTS connector_metrics (
    provider_name TEXT PRIMARY KEY,
    success_rate REAL DEFAULT 1.0,
    avg_latency_ms REAL DEFAULT 0.0,
    failure_rate REAL DEFAULT 0.0,
    rate_limit_freq REAL DEFAULT 0.0, -- 429 Frequency
    avg_jobs_per_company REAL DEFAULT 0.0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);

-- The Verified Registry (Operational View for the Monitoring Engine)
CREATE TABLE IF NOT EXISTS verified_registry (
    company_id TEXT PRIMARY KEY,
    ats_provider TEXT NOT NULL,
    ats_slug TEXT NOT NULL,
    careers_url TEXT NOT NULL,
    business_priority REAL DEFAULT 0.0,
    crawl_priority REAL DEFAULT 0.0,
    last_monitored_at TEXT,
    status TEXT DEFAULT 'ACTIVE',
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);
