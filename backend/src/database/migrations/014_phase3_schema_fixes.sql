-- 014_phase3_schema_fixes.sql
-- Fixes missing scheduler_state and recreates worker_states to match the expected interface

CREATE TABLE IF NOT EXISTS scheduler_state (
    id INTEGER PRIMARY KEY,
    state TEXT,
    version TEXT,
    started_at DATETIME,
    pid INTEGER,
    host TEXT,
    heartbeat DATETIME
);

DROP TABLE IF EXISTS worker_states;

CREATE TABLE worker_states (
    worker_id TEXT PRIMARY KEY,
    worker_name TEXT,
    worker_type TEXT,
    provider TEXT,
    pid INTEGER,
    status TEXT,
    current_company_id TEXT,
    started_at DATETIME,
    heartbeat DATETIME,
    heartbeat_timeout INTEGER,
    jobs_processed INTEGER DEFAULT 0,
    jobs_found INTEGER DEFAULT 0,
    successes INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    last_error TEXT,
    last_error_at DATETIME,
    current_task TEXT,
    cpu_percent REAL,
    memory_mb REAL,
    updated_at DATETIME
);
