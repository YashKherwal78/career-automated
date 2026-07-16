import os
import sys
import json
from pathlib import Path
try:
    import psycopg
except ImportError:
    psycopg = None

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

from src.database.migrate import MigrationRunner
from src.api.db import get_connection, is_postgres

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "postgres"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def fail(msg):
    print(f"FAILED: {msg}", file=sys.stderr)
    sys.exit(1)

def run():
    print("Running Phase 2: PostgreSQL Schema Creation...")
    
    if not is_postgres():
        fail("DATABASE_URL is not configured for PostgreSQL.")
        
    # 1. Apply existing migrations
    try:
        print("Applying migration chain...")
        # MigrationRunner doesn't strictly need a valid db_path when using Postgres as it uses get_connection()
        runner = MigrationRunner("dummy.db") 
        runner.run_migrations()
        print("Migration chain applied successfully.")
    except Exception as e:
        fail(f"Migration failed: {e}")
        
    # 2. Verify Schema Details via metadata queries
    conn = get_connection()
    try:
        cursor = conn.execute('''
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE';
        ''')
        tables = [row[0] if isinstance(row, tuple) else row["table_name"] for row in cursor.fetchall()]
        
        def get_count(q):
            c = conn.execute(q)
            row = c.fetchone()
            if not row: return 0
            if isinstance(row, tuple): return row[0]
            if isinstance(row, dict): return list(row.values())[0]
            # fallback for psycopg3 RealDictRow or similar
            try: return row[0]
            except KeyError: return list(row.keys())[0]

        index_count = get_count("SELECT count(*) FROM pg_indexes WHERE schemaname = 'public';")
        constraint_count = get_count("SELECT count(*) FROM information_schema.table_constraints WHERE table_schema = 'public';")
        pk_count = get_count("SELECT count(*) FROM information_schema.table_constraints WHERE table_schema = 'public' AND constraint_type = 'PRIMARY KEY';")
        fk_count = get_count("SELECT count(*) FROM information_schema.table_constraints WHERE table_schema = 'public' AND constraint_type = 'FOREIGN KEY';")
        
    except Exception as e:
        fail(f"Failed to verify schema metadata: {e}")
    finally:
        conn.close()
        
    if "schema_migrations" not in tables:
        fail("schema_migrations table was not created.")
        
    # 3. Generate Reports
    schema_report = {
        "status": "PASS",
        "tables_created": len(tables),
        "tables": tables,
        "indexes": index_count,
        "constraints": constraint_count,
        "primary_keys": pk_count,
        "foreign_keys": fk_count,
        "migration_failures": 0,
        "ready_for_phase_2_5": True
    }
    
    with open(ARTIFACTS_DIR / "schema_report.json", "w") as f:
        json.dump(schema_report, f, indent=2)
        
    summary_md = [
        "# PostgreSQL Schema Creation Summary",
        "",
        "## Status: ✅ PASS",
        "",
        "### Schema Verification",
        f"- **Tables Created**: {len(tables)}",
        f"- **Indexes**: {index_count}",
        f"- **Total Constraints**: {constraint_count}",
        f"- **Primary Keys**: {pk_count}",
        f"- **Foreign Keys**: {fk_count}",
        "",
        "### Details",
        f"- **Migration Failures**: 0",
        "- **schema_migrations table**: ✅ Present",
        "",
        "### Readiness",
        "The database schema is fully initialized and ready for **Repository Compatibility Tests (02_verify_schema.py)**."
    ]
    
    with open(ARTIFACTS_DIR / "schema_summary.md", "w") as f:
        f.write("\n".join(summary_md))
        
    print("\n" + "="*50)
    print(f"Status: PASS")
    print(f"Tables created: {len(tables)}")
    print(f"Indexes: {index_count}")
    print(f"Constraints: {constraint_count}")
    print(f"Migration failures: 0")
    print("Database is READY for Repository Compatibility Tests (02_verify_schema.py).")
    print("="*50)

if __name__ == "__main__":
    run()
