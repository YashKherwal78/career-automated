import sys
import sqlite3

sys.path.append('.')
from src.api.db import get_connection

def migrate_platform():
    conn = get_connection()
    try:
        print("Migrating schema...")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT UNIQUE,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.execute("INSERT OR IGNORE INTO schema_version (version) VALUES ('v1')")

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
        
        new_columns = [
            ("crawl_event_id", "TEXT"),
            ("jobs_inserted", "INTEGER"),
            ("jobs_updated", "INTEGER"),
            ("jobs_archived", "INTEGER"),
            ("crawl_duration_ms", "REAL"),
            ("response_status", "INTEGER"),
            ("provider_latency_ms", "REAL"),
            ("parser_version", "TEXT"),
            ("connector_version", "TEXT")
        ]
        
        for col_name, col_type in new_columns:
            try:
                conn.execute(f"ALTER TABLE company_crawl_history ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name} to company_crawl_history.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print(f"Column {col_name} already exists in company_crawl_history.")
                else:
                    print(f"Error adding {col_name} to company_crawl_history: {e}")

        conn.commit()
        print("Migration complete.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_platform()
