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
