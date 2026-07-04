CREATE TABLE IF NOT EXISTS crawl_runs (
    id TEXT PRIMARY KEY,
    connector TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    pages INTEGER DEFAULT 0,
    companies_found INTEGER DEFAULT 0,
    new_companies INTEGER DEFAULT 0,
    duplicates INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    status TEXT NOT NULL
);
