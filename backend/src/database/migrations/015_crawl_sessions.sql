-- 015_crawl_sessions.sql
-- Fixes missing crawl_sessions table used by SessionRepository

CREATE TABLE IF NOT EXISTS crawl_sessions (
    session_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    status TEXT DEFAULT 'RUNNING',
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    jobs_found INTEGER DEFAULT 0,
    candidates_found INTEGER DEFAULT 0,
    companies_processed INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0
);
