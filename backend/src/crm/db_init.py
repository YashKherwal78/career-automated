import sqlite3
import os
import sys
import glob

# Ensure absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.system.logger import setup_logger

logger = setup_logger("DBInit")

DB_PATH = "data/crm.db"

def init_db():
    logger.info(f"Checking database at {DB_PATH}")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if schema_version exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
    if not cursor.fetchone():
        logger.info("Fresh database detected (or pre-versioning). Initializing schema_version.")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # If there are tables but no schema_version, assume it's at v1
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        if len(tables) > 1: # More than just schema_version
            cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")
        else:
            cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (0)")
        conn.commit()

    cursor.execute("SELECT MAX(version) FROM schema_version")
    current_version = cursor.fetchone()[0] or 0
    logger.info(f"Current schema version: {current_version}")
    
    # Look for schema_v*.sql files and apply them sequentially
    schema_files = glob.glob("src/crm/schema_v*.sql")
    schema_files.sort() # Ensure correct order
    
    for sf in schema_files:
        # Extract version number (e.g., 'src/crm/schema_v1.sql' -> 1)
        base = os.path.basename(sf)
        v_str = base.replace("schema_v", "").split(".")[0]
        try:
            v_num = int(v_str)
        except ValueError:
            continue
            
        if v_num > current_version:
            logger.info(f"Applying migration: {base} (Version {v_num})")
            with open(sf, 'r') as f:
                sql_script = f.read()
            try:
                cursor.executescript(sql_script)
                cursor.execute("INSERT INTO schema_version (version) VALUES (?)", (v_num,))
                conn.commit()
                logger.info(f"Successfully applied version {v_num}")
                current_version = v_num
            except Exception as e:
                logger.error(f"Failed to apply {base}: {e}")
                conn.rollback()
                raise
                
    conn.close()
    logger.info("Database initialization complete.")

if __name__ == "__main__":
    init_db()
