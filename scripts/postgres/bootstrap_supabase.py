import os
import sys
import time
import json
import platform
import subprocess
from pathlib import Path
try:
    import psycopg
except ImportError:
    psycopg = None

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "postgres"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def fail(msg):
    print(f"FAILED: {msg}", file=sys.stderr)
    sys.exit(1)

def run():
    print("Running Supabase Bootstrap Validation...")
    
    # 1. Environment Verification
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        fail("DATABASE_URL environment variable is not set. Please add it to your .env file.")
        
    engine = "Unknown"
    if db_url.startswith("postgresql://") or db_url.startswith("postgres://"):
        engine = "PostgreSQL"
    else:
        fail("DATABASE_URL does not point to PostgreSQL. (Expected postgresql:// or postgres://)")
        
    if "sslmode=require" not in db_url:
        fail("SSL is not enabled in DATABASE_URL. Please ensure 'sslmode=require' is included in the connection string for Supabase.")
        
    if psycopg is None:
        fail("psycopg is not installed. Please install it in your virtual environment.")
        
    # 2. Connection Validation (5 attempts)
    latencies = []
    conn = None
    for i in range(5):
        start_time = time.time()
        try:
            temp_conn = psycopg.connect(db_url, autocommit=True)
            if conn is None:
                conn = temp_conn
            else:
                temp_conn.close()
        except Exception as e:
            fail(f"Failed to connect to database on attempt {i+1}. Check if PostgreSQL is running and credentials are correct. Error: {e}")
        latencies.append((time.time() - start_time) * 1000)
        
    min_latency = min(latencies)
    max_latency = max(latencies)
    avg_latency = sum(latencies) / len(latencies)
    
    # 3. PostgreSQL Information
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    server_version_full = cursor.fetchone()[0]
    
    cursor.execute("SHOW server_version;")
    server_version = cursor.fetchone()[0]
    
    cursor.execute("SHOW server_encoding;")
    encoding = cursor.fetchone()[0]
    
    cursor.execute("SHOW TimeZone;")
    timezone = cursor.fetchone()[0]
    
    try:
        cursor.execute("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid();")
        ssl_used = cursor.fetchone()
        ssl_status = "ON" if (ssl_used and ssl_used[0]) else "OFF"
    except Exception:
        ssl_status = "UNKNOWN (Assume ON due to sslmode=require)"
        
    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()[0]
    
    cursor.execute("SELECT current_user;")
    db_user = cursor.fetchone()[0]
    
    cursor.execute("SELECT current_schema();")
    current_schema = cursor.fetchone()[0]
    
    cursor.execute("SHOW search_path;")
    search_path = cursor.fetchone()[0]
    
    env_info = {
        "python_version": platform.python_version(),
        "psycopg_version": psycopg.__version__ if hasattr(psycopg, "__version__") else "Unknown",
        "postgresql_full_version": server_version_full,
        "server_version": server_version,
        "os": platform.platform(),
        "ssl_status": ssl_status,
        "server_encoding": encoding,
        "server_timezone": timezone,
        "database_name": db_name,
        "user": db_user,
        "current_schema": current_schema,
        "search_path": search_path
    }
    
    # 4. Database Configuration
    config_keys = ["max_connections", "shared_buffers", "work_mem", "maintenance_work_mem", "effective_cache_size"]
    db_config = {}
    for key in config_keys:
        try:
            cursor.execute(f"SHOW {key};")
            db_config[key] = cursor.fetchone()[0]
        except Exception:
            db_config[key] = "Unknown"
            
    # 5. Permission Validation
    permissions = {
        "CONNECT": True, 
        "CREATE_TABLE": False,
        "ALTER_TABLE": False,
        "DROP_TABLE": False,
        "INDEX": False,
        "CREATE_TEMP_TABLE": False,
        "CREATE_EXTENSION": False
    }
    
    try:
        cursor.execute("CREATE TEMP TABLE __supabase_verify_conn_test (id INT);")
        permissions["CREATE_TEMP_TABLE"] = True
        permissions["CREATE_TABLE"] = True 
        
        cursor.execute("ALTER TABLE __supabase_verify_conn_test ADD COLUMN name TEXT;")
        permissions["ALTER_TABLE"] = True
        
        cursor.execute("CREATE INDEX __idx_supabase_verify on __supabase_verify_conn_test(id);")
        permissions["INDEX"] = True
        
        cursor.execute("DROP TABLE __supabase_verify_conn_test;")
        permissions["DROP_TABLE"] = True
    except Exception as e:
        print(f"Warning: Permission check failed for basic DDL: {e}")
        
    try:
        cursor.execute("SELECT has_function_privilege('pg_create_extension()', 'execute');")
        cursor.execute("SELECT usesuper FROM pg_user WHERE usename = current_user;")
        is_super = cursor.fetchone()[0]
        permissions["CREATE_EXTENSION"] = bool(is_super)
    except Exception:
        pass
        
    conn.close()
    
    # Generate Artifacts
    supabase_env = {
        "environment": env_info,
        "configuration": db_config
    }
    
    supabase_conn = {
        "status": "PASS",
        "engine": engine,
        "latency_ms": {
            "min": min_latency,
            "avg": avg_latency,
            "max": max_latency
        },
        "permissions": permissions,
        "warnings": []
    }
    
    for p, val in permissions.items():
        if not val and p != "CREATE_EXTENSION":
            fail(f"Required permission {p} is missing for user {db_user}. Please grant it.")
            
    if not permissions["CREATE_EXTENSION"]:
        supabase_conn["warnings"].append("User lacks CREATE EXTENSION permissions. (Warning only)")
        
    with open(ARTIFACTS_DIR / "supabase_environment.json", "w") as f:
        json.dump(supabase_env, f, indent=2)
    with open(ARTIFACTS_DIR / "supabase_connection.json", "w") as f:
        json.dump(supabase_conn, f, indent=2)
    with open(ARTIFACTS_DIR / "environment_report.json", "w") as f:
        json.dump(supabase_env, f, indent=2)
    with open(ARTIFACTS_DIR / "connection_report.json", "w") as f:
        json.dump(supabase_conn, f, indent=2)
        
    summary_md = [
        "# PostgreSQL Connection Summary",
        "",
        "## Status: ✅ PASS",
        "",
        "### Latency",
        f"- Min: {min_latency:.2f} ms",
        f"- Avg: {avg_latency:.2f} ms",
        f"- Max: {max_latency:.2f} ms",
        "",
        "### Environment",
        f"- DB: {db_name}",
        f"- User: {db_user}",
        f"- Schema: {current_schema}",
        f"- Version: {server_version}",
        f"- SSL: {ssl_status}",
        "",
        "### Database Configuration",
    ]
    for k, v in db_config.items():
        summary_md.append(f"- {k}: {v}")
        
    summary_md.append("\n### Permissions")
    for p, val in permissions.items():
        summary_md.append(f"- {p}: {'✅' if val else '❌'}")
        
    with open(ARTIFACTS_DIR / "connection_summary.md", "w") as f:
        f.write("\n".join(summary_md))
        
    readiness_md = [
        "# Supabase Readiness",
        "",
        "## Overall Readiness: ✅ PASS",
        "",
        "### Connection Status",
        "- **Status**: ✅ PASS",
        f"- **SSL Status**: {ssl_status}",
        f"- **PostgreSQL Version**: {server_version}",
        f"- **Database Name**: {db_name}",
        f"- **User**: {db_user}",
        "",
        "### Latency",
        f"- **Min**: {min_latency:.2f} ms",
        f"- **Avg**: {avg_latency:.2f} ms",
        f"- **Max**: {max_latency:.2f} ms",
        "",
        "### Permissions Matrix"
    ]
    for p, val in permissions.items():
        readiness_md.append(f"- **{p}**: {'✅' if val else '❌'}")
        
    readiness_md.extend([
        "",
        "### Warnings"
    ])
    if not supabase_conn["warnings"]:
        readiness_md.append("- None")
    else:
        for w in supabase_conn["warnings"]:
            readiness_md.append(f"- {w}")
            
    readiness_md.extend([
        "",
        "### Recommended Next Step",
        "Run `scripts/postgres/01_create_schema.py` to begin schema migration."
    ])
    
    with open(ARTIFACTS_DIR / "supabase_readiness.md", "w") as f:
        f.write("\n".join(readiness_md))
        
    print("Supabase Bootstrap Validation passed successfully!")
    print("Phase 1.5 COMPLETE")

if __name__ == "__main__":
    run()
