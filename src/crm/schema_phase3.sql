-- Crawl Budgets & Global Limits
CREATE TABLE IF NOT EXISTS global_crawl_budget (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- Single row table
    max_requests_per_hour INTEGER DEFAULT 5000,
    max_requests_per_provider INTEGER DEFAULT 1000,
    max_concurrent_workers INTEGER DEFAULT 30,
    max_web_searches_per_day INTEGER DEFAULT 3000,
    current_hour_requests INTEGER DEFAULT 0,
    current_day_searches INTEGER DEFAULT 0,
    last_reset_hour TEXT,
    last_reset_day TEXT
);

-- Provider Metrics
CREATE TABLE IF NOT EXISTS provider_metrics (
    provider_name TEXT PRIMARY KEY,
    jobs_discovered INTEGER DEFAULT 0,
    jobs_changed INTEGER DEFAULT 0,
    avg_latency_ms REAL DEFAULT 0.0,
    error_rate REAL DEFAULT 0.0,
    rate_limit_freq REAL DEFAULT 0.0, -- 429 Frequency
    total_cost REAL DEFAULT 0.0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Extended Career Endpoints (Health Score & Crawl History Hashing)
-- Since career_endpoints exists, we will alter it (or recreate if needed for this script)
-- Note: SQLite ALTER TABLE is limited, so we will just add the new columns needed.
ALTER TABLE career_endpoints ADD COLUMN endpoint_health_score REAL DEFAULT 0.0;
ALTER TABLE career_endpoints ADD COLUMN evidence JSON;
ALTER TABLE career_endpoints ADD COLUMN last_crawl TEXT;
ALTER TABLE career_endpoints ADD COLUMN last_success TEXT;
ALTER TABLE career_endpoints ADD COLUMN last_job_count INTEGER DEFAULT 0;
ALTER TABLE career_endpoints ADD COLUMN last_job_hash TEXT;
ALTER TABLE career_endpoints ADD COLUMN avg_response_time REAL DEFAULT 0.0;
ALTER TABLE career_endpoints ADD COLUMN cache_ttl_days INTEGER DEFAULT 30;

-- Split Retry Queues
CREATE TABLE IF NOT EXISTS discovery_retry_queue (
    company_id TEXT PRIMARY KEY,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);

CREATE TABLE IF NOT EXISTS monitoring_retry_queue (
    endpoint_id TEXT PRIMARY KEY,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(endpoint_id) REFERENCES career_endpoints(endpoint_id)
);
