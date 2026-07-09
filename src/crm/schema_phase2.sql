-- Career Endpoints (One-to-Many relationship with companies)
CREATE TABLE IF NOT EXISTS career_endpoints (
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
    last_verified_at TEXT,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);

-- Discovery Knowledge Base (Permanent Patterns)
CREATE TABLE IF NOT EXISTS discovery_knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT NOT NULL,
    pattern TEXT NOT NULL,
    ats_provider TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Pipeline Runs (Mutable Tracking)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    pipeline_version TEXT,
    intent_version TEXT,
    match_version TEXT,
    ranker_version TEXT,
    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'RUNNING'
);

-- Raw Jobs (Immutable Payload from Crawler/Canonicalizer)
CREATE TABLE IF NOT EXISTS raw_jobs (
    fingerprint TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    provider TEXT,
    provider_job_id TEXT,
    normalized_title TEXT,
    normalized_location TEXT,
    normalized_employment_type TEXT,
    raw_payload_json TEXT NOT NULL,
    source_trust_score INTEGER DEFAULT 50,
    payload_quality_score INTEGER DEFAULT 0,
    discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
);

-- Job States (Mutable pipeline evaluations)
CREATE TABLE IF NOT EXISTS job_states (
    fingerprint TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    status TEXT DEFAULT 'DISCOVERED', -- CANONICALIZED, INTENT, MATCHED, RANKED, READY_TO_APPLY, REJECTED_INTENT, REJECTED_HARD
    
    -- Scoring Metrics
    intent_score INTEGER,
    match_score INTEGER,
    company_score INTEGER,
    priority_score INTEGER,
    
    -- Feature Vectors for ML
    feature_vector_json TEXT,
    
    -- Rejection Reason if applicable
    rejection_reason TEXT,
    
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fingerprint) REFERENCES raw_jobs(fingerprint),
    FOREIGN KEY(run_id) REFERENCES pipeline_runs(run_id)
);

-- Retry Queue for pipeline failures
CREATE TABLE IF NOT EXISTS retry_queue (
    retry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint TEXT NOT NULL,
    failed_stage TEXT NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fingerprint) REFERENCES raw_jobs(fingerprint)
);

-- Applications (Mutable tracking for when a job is applied to)
CREATE TABLE IF NOT EXISTS applications (
    application_id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    resume_version TEXT,
    intent_score_at_time INTEGER,
    match_score_at_time INTEGER,
    priority_score_at_time INTEGER,
    status TEXT DEFAULT 'APPLIED', -- APPLIED, FAILED
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fingerprint) REFERENCES raw_jobs(fingerprint)
);

-- Responses (Mutable tracking for outcomes)
CREATE TABLE IF NOT EXISTS responses (
    application_id TEXT PRIMARY KEY,
    reply_received INTEGER DEFAULT 0,
    interview_received INTEGER DEFAULT 0,
    offer_received INTEGER DEFAULT 0,
    rejected INTEGER DEFAULT 0,
    response_date TEXT,
    FOREIGN KEY(application_id) REFERENCES applications(application_id)
);
