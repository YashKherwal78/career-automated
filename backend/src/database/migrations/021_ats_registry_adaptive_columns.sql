-- Migration: 021_ats_registry_adaptive_columns
-- Implements provider health configurations, adaptive recrawl structures, transactional outboxes, and safe expand-contract timestamp columns.

-- 1. Create provider health and scheduling telemetry tables
CREATE TABLE IF NOT EXISTS provider_health (
    provider_id TEXT PRIMARY KEY REFERENCES ats_providers(provider_id),
    consecutive_429s INTEGER DEFAULT 0,
    backoff_until TIMESTAMP WITH TIME ZONE,
    avg_latency_ms REAL DEFAULT 0.0,
    total_successes INTEGER DEFAULT 0,
    total_failures INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS provider_scheduler (
    provider_id TEXT PRIMARY KEY REFERENCES ats_providers(provider_id),
    desired_workers INTEGER DEFAULT 1,
    current_workers INTEGER DEFAULT 1,
    backlog INTEGER DEFAULT 0,
    throughput REAL DEFAULT 0.0,
    last_scheduler_run TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create transactional outbox events table
CREATE TABLE IF NOT EXISTS outbox_events (
    event_id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, PROCESSING, DELIVERED, FAILED
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP WITH TIME ZONE,
    correlation_id UUID,
    trace_id UUID
);

-- 3. Add adaptive recrawl, lease fencing, and safe expand columns to ats_registry
ALTER TABLE ats_registry
    ADD COLUMN IF NOT EXISTS crawl_tier TEXT DEFAULT 'NORMAL',
    ADD COLUMN IF NOT EXISTS crawl_interval_hours INTEGER DEFAULT 8,
    ADD COLUMN IF NOT EXISTS rolling_churn_percent REAL DEFAULT 0.0,
    ADD COLUMN IF NOT EXISTS crawls_in_current_tier INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS decision_reason TEXT DEFAULT 'INITIAL_IMPORT',
    ADD COLUMN IF NOT EXISTS last_tier_change TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS lease_token TEXT,
    ADD COLUMN IF NOT EXISTS lease_epoch INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_check_at_tz TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS reserved_until_tz TIMESTAMP WITH TIME ZONE;

-- 4. Safe Expand Backfill: Migrate numeric epoch values to new TIMESTAMPTZ columns
UPDATE ats_registry
SET next_check_at_tz = CASE 
        WHEN next_check_at IS NOT NULL AND next_check_at > 0 
        THEN to_timestamp(next_check_at) 
        ELSE NULL 
    END,
    reserved_until_tz = CASE 
        WHEN reserved_until IS NOT NULL AND reserved_until > 0 
        THEN to_timestamp(reserved_until) 
        ELSE NULL 
    END;

-- 5. Add index structures for high-performance scheduling and outbox retry queries
CREATE INDEX IF NOT EXISTS idx_ats_registry_scheduler_tz ON ats_registry(status, provider_id, next_check_at_tz, priority);
CREATE INDEX IF NOT EXISTS idx_outbox_retry ON outbox_events(status, next_retry_at);
