-- 006_automated_company_discovery.sql
-- Track metadata for company seeds discovered by SeedDiscoveryWorker.
--
-- Single source of truth: this schema matches src/crm/database.py (line 281)
-- and src/workers/seed_discovery_worker.py. Do not invent a second schema here.

CREATE TABLE IF NOT EXISTS company_discovery_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name    TEXT    NOT NULL,
    source          TEXT    NOT NULL,      -- ycombinator, search, techstars, etc.
    discovery_type  TEXT,                  -- e.g. 'automated'
    first_seen      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen       DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence      INTEGER  DEFAULT 1,
    reliability_score REAL   DEFAULT 0.5,
    UNIQUE(company_name, source, discovery_type)
);
