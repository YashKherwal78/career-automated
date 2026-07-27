-- Migration 025: Evidence-Based Forensics System

-- Track connector deployments natively
CREATE TABLE IF NOT EXISTS connector_versions (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    connector_name TEXT NOT NULL,
    git_commit TEXT,
    created_at REAL NOT NULL
);

-- O(1) Yield Regression Tracking
CREATE TABLE IF NOT EXISTS board_statistics (
    board_id TEXT PRIMARY KEY,
    rolling_mean REAL DEFAULT 0,
    rolling_stddev REAL DEFAULT 0,
    rolling_count INTEGER DEFAULT 0,
    last_updated REAL NOT NULL
);

-- Operational crawl metadata (Every crawl)
CREATE TABLE IF NOT EXISTS crawl_metadata (
    crawl_id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    connector_name TEXT NOT NULL,
    started_at REAL NOT NULL,
    duration_ms REAL,
    http_status INTEGER,
    content_length INTEGER,
    schema_hash TEXT,
    connector_version_id TEXT,
    jobs_extracted INTEGER,
    jobs_inserted INTEGER
);
CREATE INDEX IF NOT EXISTS idx_metadata_board ON crawl_metadata(board_id);

-- Strict 1:1 Terminal Outcome (For dashboards)
CREATE TABLE IF NOT EXISTS crawl_outcome (
    crawl_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    classification TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outcome_provider ON crawl_outcome(provider);

-- Schema Usage Stats (Mutable)
CREATE TABLE IF NOT EXISTS schema_usage (
    provider TEXT NOT NULL,
    connector_name TEXT NOT NULL,
    endpoint_family TEXT NOT NULL,
    schema_hash TEXT NOT NULL,
    first_seen REAL,
    last_seen REAL,
    seen_count INTEGER DEFAULT 1,
    PRIMARY KEY (provider, connector_name, endpoint_family, schema_hash)
);
DROP TABLE IF EXISTS board_snapshots;
