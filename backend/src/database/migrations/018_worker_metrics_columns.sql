-- 018_worker_metrics_columns.sql
-- Add missing columns to worker_metrics that telemetry.py expects

ALTER TABLE worker_metrics ADD COLUMN failed INTEGER DEFAULT 0;
ALTER TABLE worker_metrics ADD COLUMN avg_latency REAL DEFAULT 0.0;

-- Ensure pipeline_stage_metrics exists with correct schema
CREATE TABLE IF NOT EXISTS pipeline_stage_metrics (
    stage TEXT PRIMARY KEY,
    processed INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    avg_latency REAL DEFAULT 0.0,
    p95 REAL DEFAULT 0.0,
    p99 REAL DEFAULT 0.0
);
