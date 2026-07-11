-- 008_job_board_snapshots.sql
-- Tracks per-provider sync state for Pipeline B (job board discovery).
-- The cursor column stores provider-specific pagination state (page token,
-- etag, offset, etc.) so each sync can resume incrementally.

CREATE TABLE IF NOT EXISTS job_board_snapshots (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    provider             TEXT    NOT NULL,
    synced_at            REAL    NOT NULL DEFAULT (unixepoch('now')),
    cursor               TEXT,              -- next_page_token / etag / offset
    jobs_found           INTEGER DEFAULT 0,
    jobs_new             INTEGER DEFAULT 0,
    jobs_updated         INTEGER DEFAULT 0,
    duplicates           INTEGER DEFAULT 0,
    companies_discovered INTEGER DEFAULT 0, -- how many enqueued into Pipeline A
    status               TEXT    DEFAULT 'SUCCESS',
    error                TEXT
);

CREATE INDEX IF NOT EXISTS idx_job_board_snapshots_provider
    ON job_board_snapshots (provider, synced_at DESC);
