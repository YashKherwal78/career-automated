import os
import sys
import sqlite3

sys.path.append('.')

from src.api.db import get_connection

def get_csv_providers():
    providers = []
    directory = 'research/ats-scrapers-main/ats-companies'
    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            provider_name = filename[:-4]
            providers.append(provider_name)
    return providers

def init_schema():
    conn = get_connection()
    try:
        print("Creating company_master...")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS company_master (
            company_id TEXT PRIMARY KEY,
            company_name TEXT,
            domain TEXT UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        print("Creating unverified_companies...")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS unverified_companies (
            company_id TEXT PRIMARY KEY,
            discovery_source TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        print("Creating providers...")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id TEXT PRIMARY KEY,
            name TEXT,
            concurrency INTEGER DEFAULT 5,
            crawl_interval INTEGER DEFAULT 86400,
            enabled INTEGER DEFAULT 1,
            priority TEXT DEFAULT 'MEDIUM',
            rate_limit INTEGER DEFAULT 100,
            min_workers INTEGER DEFAULT 1,
            current_workers INTEGER DEFAULT 1,
            max_workers INTEGER DEFAULT 10,
            promotion_threshold REAL DEFAULT 0.20,
            demotion_threshold REAL DEFAULT 0.02,
            critical_interval INTEGER DEFAULT 2,
            high_interval INTEGER DEFAULT 4,
            normal_interval INTEGER DEFAULT 8,
            low_interval INTEGER DEFAULT 12,
            dormant_interval INTEGER DEFAULT 24
        )
        """)
        
        print("Creating operational tables...")
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
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT UNIQUE,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        print("Creating scheduler and worker states...")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            state TEXT DEFAULT 'STOPPED',
            heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
            version TEXT,
            started_at DATETIME,
            pid INTEGER,
            host TEXT
        )
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS worker_states (
            worker_id TEXT PRIMARY KEY,
            status TEXT,
            provider TEXT,
            company_id TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
            heartbeat_timeout INTEGER DEFAULT 60
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS company_crawl_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT,
            provider TEXT,
            crawl_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            duration REAL,
            status TEXT,
            jobs_found INTEGER,
            error TEXT,
            session_id TEXT,
            crawl_event_id TEXT,
            jobs_inserted INTEGER,
            jobs_updated INTEGER,
            jobs_archived INTEGER,
            crawl_duration_ms REAL,
            response_status INTEGER,
            provider_latency_ms REAL,
            parser_version TEXT,
            connector_version TEXT
        )
        """)
        
        # Insert initial schema version
        conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES ('v1')")
        
        providers = get_csv_providers()
        print(f"Found {len(providers)} providers from CSV files.")
        
        for provider in providers:
            # We want to replace non-alphanumeric chars (e.g. infojobs_es is fine, but jobs_cz has underscore. All alphanumeric/underscore is fine)
            safe_provider = "".join([c if c.isalnum() else '_' for c in provider])
            print(f"Initializing schema and metadata for provider: {safe_provider}")
            
            # Insert into providers table
            conn.execute("""
            INSERT INTO providers (id, name, concurrency, max_workers)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """, (safe_provider, safe_provider.capitalize(), 5, 10))
            
            # Create registry_{provider}
            conn.execute(f"""
            CREATE TABLE IF NOT EXISTS registry_{safe_provider} (
                company_id TEXT PRIMARY KEY,
                company_name TEXT,
                endpoint TEXT,
                priority TEXT DEFAULT 'MEDIUM',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Create registry_{provider}_state
            conn.execute(f"""
            CREATE TABLE IF NOT EXISTS registry_{safe_provider}_state (
                company_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'QUEUED',
                crawl_lock INTEGER DEFAULT 0,
                locked_at DATETIME,
                worker_id TEXT,
                next_crawl DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_crawl DATETIME,
                previous_jobs INTEGER DEFAULT 0,
                current_jobs INTEGER DEFAULT 0,
                job_delta INTEGER DEFAULT 0,
                last_success DATETIME,
                last_error TEXT,
                consecutive_failures INTEGER DEFAULT 0,
                total_success INTEGER DEFAULT 0,
                total_failures INTEGER DEFAULT 0,
                health_score REAL DEFAULT 100.0,
                crawl_tier TEXT DEFAULT 'NORMAL',
                crawl_interval_hours INTEGER DEFAULT 8,
                rolling_churn_percent REAL DEFAULT 0.0,
                crawls_in_current_tier INTEGER DEFAULT 0,
                last_tier_change DATETIME DEFAULT CURRENT_TIMESTAMP,
                decision_reason TEXT DEFAULT 'INITIAL_IMPORT',
                manual_override_enabled INTEGER DEFAULT 0,
                manual_interval_hours INTEGER,
                manual_tier TEXT,
                FOREIGN KEY(company_id) REFERENCES registry_{safe_provider}(company_id)
            )
            """)
            
        conn.commit()
        print("Schema initialization complete.")
    except Exception as e:
        print(f"Error initializing schema: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    init_schema()
