import sys, sqlite3, os
sys.path.append('.')
from src.api.db import get_connection

conn = get_connection()
conn.execute("DROP TABLE IF EXISTS crawl_sessions")
conn.execute("""
CREATE TABLE IF NOT EXISTS crawl_sessions (
    session_id TEXT,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    provider TEXT,
    companies_attempted INTEGER DEFAULT 0,
    companies_success INTEGER DEFAULT 0,
    companies_failed INTEGER DEFAULT 0,
    jobs_discovered INTEGER DEFAULT 0,
    c429_count INTEGER DEFAULT 0,
    timeout_count INTEGER DEFAULT 0,
    avg_latency REAL DEFAULT 0.0,
    avg_workers INTEGER DEFAULT 0,
    status TEXT DEFAULT 'RUNNING',
    PRIMARY KEY (session_id, provider)
)
""")
conn.commit()
conn.close()
