-- 010_pipeline_scaling.sql
-- Add lifecycle_state to company_identities and worker progress/metrics tracking.

CREATE TABLE IF NOT EXISTS worker_progress (
    worker_name TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    last_checkpoint TEXT,
    batch_number INTEGER DEFAULT 0,
    processed INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    retry_count INTEGER DEFAULT 0,
    companies_per_min REAL DEFAULT 0.0,
    eta TEXT,
    queue_depth INTEGER DEFAULT 0,
    memory_usage REAL DEFAULT 0.0,
    cpu_usage REAL DEFAULT 0.0,
    last_error TEXT,
    worker_version TEXT,
    git_commit TEXT,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS worker_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    worker TEXT NOT NULL,
    processed INTEGER DEFAULT 0,
    queue_depth INTEGER DEFAULT 0,
    rate REAL DEFAULT 0.0,
    cpu REAL DEFAULT 0.0,
    memory REAL DEFAULT 0.0,
    eta REAL DEFAULT 0.0
);
