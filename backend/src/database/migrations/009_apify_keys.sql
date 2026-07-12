-- Migration 009: Create apify_keys and apify_analytics tables for ApifyManager
CREATE TABLE IF NOT EXISTS apify_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_var_name TEXT NOT NULL UNIQUE,
    status TEXT DEFAULT 'ACTIVE',
    credits_used REAL DEFAULT 0.0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    runs_executed INTEGER DEFAULT 0,
    last_used TEXT,
    last_used_at TEXT,
    last_success TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS apify_analytics (
    category TEXT PRIMARY KEY,
    runs INTEGER DEFAULT 0,
    credits_consumed REAL DEFAULT 0.0,
    useful_results INTEGER DEFAULT 0
);
