-- 006_automated_company_discovery.sql
-- Create table to track metadata for discovered company domains and seeds.

CREATE TABLE IF NOT EXISTS company_discovery_sources (
    company_id TEXT PRIMARY KEY,
    legal_name TEXT,
    website TEXT,
    domain TEXT,
    source TEXT NOT NULL,          -- ycombinator, search, techstars, etc.
    confidence REAL DEFAULT 1.0,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL
);
