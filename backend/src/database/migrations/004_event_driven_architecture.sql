-- 004_event_driven_architecture.sql
-- Setting up isolated metrics tables and the central pipeline events log

CREATE TABLE IF NOT EXISTS operational_metrics (
    metric_key TEXT PRIMARY KEY,
    metric_value TEXT,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS business_metrics (
    metric_key TEXT PRIMARY KEY,
    metric_value TEXT,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS pipeline_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL, -- CompanyDiscovered, EndpointVerified, JobsSynced, etc.
    payload TEXT NOT NULL, -- JSON string mapping event attributes
    timestamp REAL NOT NULL
);
