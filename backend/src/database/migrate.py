import sqlite3
import os
import glob
import re
from src.system.logger import setup_logger

logger = setup_logger("MigrationRunner")

class MigrationRunner:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema_version()

    def _init_schema_version(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at REAL NOT NULL
                )
            ''')
            conn.commit()

    def get_applied_versions(self) -> set:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT version FROM schema_migrations")
            return {row[0] for row in cursor.fetchall()}

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            return column_name in columns

    def run_migrations(self):
        logger.info("Starting database migrations check...")
        applied = self.get_applied_versions()
        
        migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
        migration_files = glob.glob(os.path.join(migration_dir, "*.sql"))
        migration_files.sort()

        for file_path in migration_files:
            filename = os.path.basename(file_path)
            # Match 3 digit prefix
            match = re.match(r"^(\d+)_", filename)
            if not match:
                continue
            
            version = int(match.group(1))
            if version in applied:
                continue

            logger.info(f"Applying migration: {filename} (Version {version})")
            with open(file_path, "r") as f:
                sql_content = f.read()

            statements = sql_content.split(";")
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN TRANSACTION")
                try:
                    for statement in statements:
                        statement = statement.strip()
                        if not statement:
                            continue
                        
                        # Strip SQL single-line comments starting with '--'
                        lines = []
                        for line in statement.split('\n'):
                            # Remove comments while preserving string literals
                            # Simple split by '--' is sufficient since no double dashes exist inside strings in our migrations
                            lines.append(line.split('--')[0])
                        cleaned_statement = '\n'.join(lines).strip()
                        if not cleaned_statement:
                            continue
                        
                        # Safe ALTER TABLE checks to prevent crashes if column exists
                        alter_match = re.match(r"(?i)ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", cleaned_statement)
                        if alter_match:
                            table_name = alter_match.group(1)
                            column_name = alter_match.group(2)
                            if self._column_exists(table_name, column_name):
                                logger.info(f"Column '{column_name}' already exists in table '{table_name}'. Skipping.")
                                continue
                        
                        conn.execute(statement)
                    
                    conn.execute("INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)", (version, os.path.getmtime(file_path)))
                    conn.commit()
                    logger.info(f"Successfully applied migration version {version}")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to apply migration {filename}: {e}")
                    raise e

        logger.info("Database migrations check complete.")

if __name__ == "__main__":
    from src.config.config import Config
    runner = MigrationRunner(Config.DATABASE_PATH)
    runner.run_migrations()
