-- 005_pipeline_metrics.sql
-- Setting up the event-driven observability and pre-aggregated metrics schema

-- Extend immutable event log table
ALTER TABLE pipeline_events ADD COLUMN run_id TEXT;
ALTER TABLE pipeline_events ADD COLUMN company_id TEXT;
ALTER TABLE pipeline_events ADD COLUMN candidate_url TEXT;
ALTER TABLE pipeline_events ADD COLUMN worker_name TEXT;
ALTER TABLE pipeline_events ADD COLUMN stage TEXT;
ALTER TABLE pipeline_events ADD COLUMN status TEXT;
ALTER TABLE pipeline_events ADD COLUMN ats_type TEXT;
ALTER TABLE pipeline_events ADD COLUMN latency_ms REAL;
ALTER TABLE pipeline_events ADD COLUMN reason_code TEXT;
ALTER TABLE pipeline_events ADD COLUMN parent_event_id TEXT;
ALTER TABLE pipeline_events ADD COLUMN telemetry_version INTEGER;

-- Pipeline Runs Table (Run-level tracking)
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    worker TEXT NOT NULL,
    started_at REAL NOT NULL,
    finished_at REAL,
    status TEXT NOT NULL, -- RUNNING, COMPLETED, FAILED
    companies_processed INTEGER DEFAULT 0,
    candidates_found INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    jobs INTEGER DEFAULT 0,
    duration_ms REAL DEFAULT 0.0,
    trigger TEXT NOT NULL, -- Cron, Manual, Webhook
    git_commit TEXT,
    config_hash TEXT,
    feature_flags TEXT -- JSON string snapshot of settings flags
);

-- Plugin Metrics (Expanded summary)
CREATE TABLE IF NOT EXISTS plugin_metrics (
    plugin TEXT PRIMARY KEY,
    companies_seen INTEGER DEFAULT 0,
    companies_with_candidates INTEGER DEFAULT 0,
    candidates_found INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    promoted INTEGER DEFAULT 0,
    boards_crawled INTEGER DEFAULT 0,
    jobs_imported INTEGER DEFAULT 0,
    duplicates INTEGER DEFAULT 0,
    dead_boards INTEGER DEFAULT 0,
    avg_latency REAL DEFAULT 0.0,
    avg_jobs_per_board REAL DEFAULT 0.0,
    precision_rate REAL DEFAULT 0.0,
    yield_rate REAL DEFAULT 0.0
);

-- ATS Scorecards
CREATE TABLE IF NOT EXISTS ats_metrics (
    ats_type TEXT PRIMARY KEY,
    companies INTEGER DEFAULT 0,
    boards INTEGER DEFAULT 0,
    jobs INTEGER DEFAULT 0,
    latency REAL DEFAULT 0.0,
    dead_boards INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0
);

-- Source Quality Metrics (Attributions)
CREATE TABLE IF NOT EXISTS source_metrics (
    source TEXT PRIMARY KEY,
    urls_produced INTEGER DEFAULT 0,
    candidates INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0,
    avg_latency REAL DEFAULT 0.0,
    precision_rate REAL DEFAULT 0.0
);

-- Pipeline Stage Performance Metrics
CREATE TABLE IF NOT EXISTS pipeline_stage_metrics (
    stage TEXT PRIMARY KEY,
    processed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    avg_latency REAL DEFAULT 0.0,
    p95 REAL DEFAULT 0.0,
    p99 REAL DEFAULT 0.0
);

-- Company Trace Table (Current State)
CREATE TABLE IF NOT EXISTS company_trace (
    company_id TEXT PRIMARY KEY,
    run_id TEXT,
    current_stage TEXT NOT NULL,
    current_worker TEXT,
    last_event TEXT,
    last_updated REAL NOT NULL
);

-- Worker Metrics Table
CREATE TABLE IF NOT EXISTS worker_metrics (
    timestamp REAL NOT NULL,
    worker TEXT PRIMARY KEY,
    processed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    avg_latency REAL DEFAULT 0.0,
    throughput REAL DEFAULT 0.0,
    queue_size INTEGER DEFAULT 0
);
