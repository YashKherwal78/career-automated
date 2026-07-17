-- 020_worker_metrics_unique_worker.sql
-- Drop the multi-column index and create a unique index on worker column to support telemetry.py's ON CONFLICT(worker)

DROP INDEX IF EXISTS idx_worker_metrics_timestamp_worker;

CREATE UNIQUE INDEX IF NOT EXISTS idx_worker_metrics_worker 
    ON worker_metrics (worker);
