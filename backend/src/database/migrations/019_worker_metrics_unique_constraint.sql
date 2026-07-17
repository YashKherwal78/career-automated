-- 019_worker_metrics_unique_constraint.sql
-- Add unique constraint on (timestamp, worker) to support ON CONFLICT upsert in telemetry.py

CREATE UNIQUE INDEX IF NOT EXISTS idx_worker_metrics_timestamp_worker 
    ON worker_metrics (timestamp, worker);
