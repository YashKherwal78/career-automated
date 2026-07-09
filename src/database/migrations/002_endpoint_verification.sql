-- 002_endpoint_verification.sql
-- Definitions for career_endpoints, ats_registry, and local_queues

CREATE TABLE IF NOT EXISTS career_endpoints (
    endpoint_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    status TEXT DEFAULT 'DISCOVERED_ENDPOINT',
    ats_provider TEXT,
    career_url TEXT NOT NULL,
    matched_html TEXT,
    redirect_chain TEXT,
    detection_method TEXT,
    confidence REAL DEFAULT 0.0,
    discovery_version TEXT DEFAULT '1.0',
    detector_version TEXT,
    health_status TEXT DEFAULT 'UNKNOWN',
    failure_reason TEXT,
    retry_after TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TEXT,
    endpoint_health_score REAL DEFAULT 0.0,
    evidence JSON,
    last_crawl TEXT,
    last_success TEXT,
    last_job_count INTEGER DEFAULT 0,
    last_job_hash TEXT,
    avg_response_time REAL DEFAULT 0.0,
    cache_ttl_days INTEGER DEFAULT 30,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);

CREATE TABLE IF NOT EXISTS ats_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT,
    company_domain TEXT,
    company_name TEXT,
    ats_type TEXT,
    endpoint TEXT,
    canonical_endpoint TEXT,
    endpoint_hash TEXT,
    status TEXT,
    discovery_source TEXT,
    search_provider TEXT,
    search_query TEXT,
    search_rank INTEGER,
    identity_score REAL,
    inspector_score REAL,
    plugin_name TEXT,
    plugin_version TEXT,
    ats_metadata TEXT,
    created_at REAL,
    last_checked REAL,
    last_verified REAL,
    recheck_after REAL,
    retired_at REAL,
    last_job_sync REAL,
    last_successful_crawl REAL,
    crawl_status TEXT,
    job_count INTEGER
);

CREATE TABLE IF NOT EXISTS local_queues (
    item_id TEXT PRIMARY KEY,
    queue_name TEXT NOT NULL,
    payload TEXT NOT NULL, -- JSON formatted dictionary
    status TEXT DEFAULT 'QUEUED', -- QUEUED, PROCESSING, DEAD
    locked_until REAL DEFAULT 0.0,
    created_at REAL NOT NULL
);
