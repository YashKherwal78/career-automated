-- 013_worker_runtime_tables.sql
-- Create unified worker states and history tables for all worker types

CREATE TABLE IF NOT EXISTS worker_states (
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

CREATE TABLE IF NOT EXISTS worker_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id TEXT,
    started_at DATETIME,
    ended_at DATETIME,
    uptime REAL,
    jobs_processed INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    reason_for_exit TEXT
);
