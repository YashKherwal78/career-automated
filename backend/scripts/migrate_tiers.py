import sys
import sqlite3

sys.path.append('.')
from src.api.db import get_connection
from backend.scripts.init_mass_execution_schema import get_csv_providers

def migrate():
    conn = get_connection()
    try:
        # 1. Update providers table
        print("Migrating providers table...")
        new_provider_cols = [
            ("promotion_threshold", "REAL DEFAULT 0.20"),
            ("demotion_threshold", "REAL DEFAULT 0.02"),
            ("critical_interval", "INTEGER DEFAULT 2"),
            ("high_interval", "INTEGER DEFAULT 4"),
            ("normal_interval", "INTEGER DEFAULT 8"),
            ("low_interval", "INTEGER DEFAULT 12"),
            ("dormant_interval", "INTEGER DEFAULT 24")
        ]
        
        for col_name, col_type in new_provider_cols:
            try:
                conn.execute(f"ALTER TABLE providers ADD COLUMN {col_name} {col_type}")
                print(f"Added {col_name} to providers.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"Column {col_name} already exists in providers.")
                else:
                    print(f"Error adding {col_name} to providers: {e}")

        # 2. Update all registry_{provider}_state tables
        providers = get_csv_providers()
        print(f"Found {len(providers)} providers to migrate.")
        
        new_state_cols = [
            ("crawl_tier", "TEXT DEFAULT 'NORMAL'"),
            ("crawl_interval_hours", "INTEGER DEFAULT 8"),
            ("rolling_churn_percent", "REAL DEFAULT 0.0"),
            ("crawls_in_current_tier", "INTEGER DEFAULT 0"),
            ("last_tier_change", "DATETIME"),
            ("decision_reason", "TEXT DEFAULT 'INITIAL_IMPORT'"),
            ("manual_override_enabled", "INTEGER DEFAULT 0"),
            ("manual_interval_hours", "INTEGER"),
            ("manual_tier", "TEXT")
        ]
        
        for provider in providers:
            safe_provider = "".join([c if c.isalnum() else '_' for c in provider])
            table_name = f"registry_{safe_provider}_state"
            print(f"Migrating table {table_name}...")
            
            # Check if table exists
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cur.fetchone():
                print(f"Table {table_name} does not exist. Skipping.")
                continue
                
            for col_name, col_type in new_state_cols:
                try:
                    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                    print(f"  Added {col_name} to {table_name}.")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" in str(e).lower():
                        pass
                    else:
                        print(f"  Error adding {col_name} to {table_name}: {e}")
                        
            # Initialize existing records
            conn.execute(f"""
                UPDATE {table_name}
                SET crawl_tier = 'NORMAL',
                    crawl_interval_hours = 8,
                    rolling_churn_percent = 0.0,
                    crawls_in_current_tier = 0,
                    decision_reason = 'INITIAL_IMPORT'
                WHERE crawl_tier IS NULL OR crawl_tier = ''
            """)

        conn.commit()
        print("Migration complete.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
