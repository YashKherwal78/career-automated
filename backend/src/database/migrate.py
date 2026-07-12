import os
import glob
import re
from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres

logger = setup_logger("MigrationRunner")

class MigrationRunner:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not is_postgres():
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_schema_version()

    def _init_schema_version(self):
        conn = get_connection()
        try:
            if is_postgres():
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at DOUBLE PRECISION NOT NULL
                    )
                ''')
            else:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at REAL NOT NULL
                    )
                ''')
            conn.commit()
        finally:
            conn.close()

    def get_applied_versions(self) -> set:
        conn = get_connection()
        try:
            cursor = conn.execute("SELECT version FROM schema_migrations")
            return {row[0] for row in cursor.fetchall()}
        finally:
            conn.close()

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        conn = get_connection()
        try:
            if is_postgres():
                cursor = conn.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
                    (table_name, column_name)
                )
                return cursor.fetchone() is not None
            else:
                cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in cursor.fetchall()]
                return column_name in columns
        finally:
            conn.close()

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
            
            conn = get_connection()
            try:
                for statement in statements:
                    statement = statement.strip()
                    if not statement:
                        continue
                    
                    # Strip SQL single-line comments starting with '--'
                    lines = []
                    for line in statement.split('\n'):
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
                logger.error(f"Failed to apply migration {filename}: {e}")
                raise e
            finally:
                conn.close()

        logger.info("Database migrations check complete.")

if __name__ == "__main__":
    from src.config.settings import settings
    runner = MigrationRunner(settings.db_path)
    runner.run_migrations()
