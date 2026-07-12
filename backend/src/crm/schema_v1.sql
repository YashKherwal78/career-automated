CREATE TABLE company_registry (
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
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE ats_capabilities (
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
CREATE TABLE discovery_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER,
    event_type TEXT NOT NULL, -- COMPANY_ADDED, ATS_CHANGED, NEW_JOBS_FOUND, CONNECTOR_FAILED
    event_payload TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES company_registry(id)
);
CREATE TABLE company_identities (
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
CREATE TABLE hiring_snapshots (
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
CREATE TABLE connector_metrics (
    provider_name TEXT PRIMARY KEY,
    success_rate REAL DEFAULT 1.0,
    avg_latency_ms REAL DEFAULT 0.0,
    failure_rate REAL DEFAULT 0.0,
    rate_limit_freq REAL DEFAULT 0.0, -- 429 Frequency
    avg_jobs_per_company REAL DEFAULT 0.0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE verified_registry (
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
CREATE TABLE candidate_companies (
                            company_id TEXT PRIMARY KEY,
                            discovery_source TEXT,
                            status TEXT DEFAULT 'PENDING_SLUG_DISCOVERY',
                            FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
                        );
CREATE TABLE career_endpoints (
    endpoint_id TEXT PRIMARY KEY, -- UUID
    company_id TEXT NOT NULL,
    status TEXT DEFAULT 'DISCOVERED_ENDPOINT', -- DISCOVERED_ENDPOINT, VERIFYING, VERIFIED, MONITORING, FAILED
    ats_provider TEXT,
    career_url TEXT NOT NULL,
    
    -- Discovery Evidence
    matched_html TEXT,
    redirect_chain TEXT,
    detection_method TEXT,
    confidence REAL DEFAULT 0.0,
    discovery_version TEXT DEFAULT '1.0',
    detector_version TEXT,
    
    -- Endpoint Health & Retries
    health_status TEXT DEFAULT 'UNKNOWN', -- HEALTHY, RATE_LIMITED, BROKEN, REDIRECTED, UNKNOWN
    failure_reason TEXT,
    retry_after TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_verified_at TEXT, endpoint_health_score REAL DEFAULT 0.0, evidence JSON, last_crawl TEXT, last_success TEXT, last_job_count INTEGER DEFAULT 0, last_job_hash TEXT, avg_response_time REAL DEFAULT 0.0, cache_ttl_days INTEGER DEFAULT 30,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);
CREATE TABLE discovery_knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    pattern TEXT NOT NULL,
    ats_provider TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE global_crawl_budget (
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
CREATE TABLE provider_metrics (
    provider_name TEXT PRIMARY KEY,
    jobs_discovered INTEGER DEFAULT 0,
    jobs_changed INTEGER DEFAULT 0,
    avg_latency_ms REAL DEFAULT 0.0,
    error_rate REAL DEFAULT 0.0,
    rate_limit_freq REAL DEFAULT 0.0, -- 429 Frequency
    total_cost REAL DEFAULT 0.0,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE discovery_retry_queue (
    company_id TEXT PRIMARY KEY,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);
CREATE TABLE monitoring_retry_queue (
    endpoint_id TEXT PRIMARY KEY,
    failure_reason TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(endpoint_id) REFERENCES career_endpoints(endpoint_id)
);
CREATE TABLE crawl_runs (
    id TEXT PRIMARY KEY,
    connector TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    pages INTEGER DEFAULT 0,
    companies_found INTEGER DEFAULT 0,
    new_companies INTEGER DEFAULT 0,
    duplicates INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    status TEXT NOT NULL
);
CREATE TABLE crawl_cursors (connector_name TEXT PRIMARY KEY, last_page INTEGER DEFAULT 1, last_cursor TEXT);
CREATE TABLE connector_cache (
                source TEXT PRIMARY KEY,
                raw_json TEXT,
                last_updated TEXT,
                etag TEXT,
                checksum TEXT,
                normalization_version INTEGER
            );
CREATE TABLE company_cache (
                company_id TEXT PRIMARY KEY,
                json TEXT,
                last_updated TEXT
            );
CREATE TABLE source_health (
                source_name TEXT PRIMARY KEY,
                last_success TEXT,
                last_failure TEXT,
                consecutive_failures INTEGER DEFAULT 0,
                avg_latency REAL DEFAULT 0.0
            );
CREATE TABLE sync_runs (
        sync_run_id TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        started_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        status TEXT DEFAULT 'RUNNING',
        endpoints_processed INTEGER DEFAULT 0,
        jobs_added INTEGER DEFAULT 0,
        jobs_updated INTEGER DEFAULT 0,
        jobs_closed INTEGER DEFAULT 0,
        failures INTEGER DEFAULT 0,
        avg_response_time REAL DEFAULT 0.0
    );
CREATE TABLE normalized_jobs (
        job_id TEXT PRIMARY KEY,
        provider_job_id TEXT,
        company_id TEXT,
        provider TEXT,
        title TEXT,
        department TEXT,
        team TEXT,
        location TEXT,
        country TEXT,
        remote_type TEXT,
        employment_type TEXT,
        salary_min REAL,
        salary_max REAL,
        currency TEXT,
        posted_at TEXT,
        updated_at TEXT,
        apply_url TEXT,
        description TEXT,
        requirements TEXT,
        benefits TEXT,
        skills TEXT,
        job_hash TEXT,
        last_seen TEXT,
        status TEXT DEFAULT 'ACTIVE',
        closed_at TEXT,
        sync_run_id TEXT,
        raw_payload_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP, job_score REAL DEFAULT 0.0, resume_score REAL DEFAULT 0.0, company_score REAL DEFAULT 0.0, interview_probability REAL, score_breakdown TEXT, match_score REAL DEFAULT 0.0, priority_score REAL DEFAULT 0.0, scoring_confidence REAL DEFAULT 1.0, recommendation_reason TEXT, application_status TEXT DEFAULT 'Not Applied',
        FOREIGN KEY(company_id) REFERENCES company_identities(company_id),
        FOREIGN KEY(sync_run_id) REFERENCES sync_runs(sync_run_id)
    );
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    active_profile TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE user_profiles (
    profile_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    profile_name TEXT NOT NULL,
    config_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE contacts (
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
CREATE TABLE applications (
    application_id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES normalized_jobs(job_id),
    user_id TEXT REFERENCES users(user_id),
    resume_variant TEXT,
    status TEXT DEFAULT 'APPLIED',
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT OR IGNORE INTO schema_version (version) VALUES (1);
