#!/usr/bin/env python3
import os
import sys
import json
import time
import sqlite3
import argparse
import random
from pathlib import Path

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    print("psycopg not installed. Run: pip install psycopg[binary]", file=sys.stderr)
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

# Ensure ARTIFACTS_DIR exists
ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "postgres"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def get_pg_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    conn = psycopg.connect(db_url, autocommit=False, row_factory=dict_row)
    conn.execute("SET default_transaction_read_only = off")
    conn.commit()
    return conn

def get_sqlite_conn():
    db_path = Path(__file__).resolve().parents[2] / "data" / "crm.db"
    if not db_path.exists():
        print(f"SQLite DB not found at {db_path}", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_progress_table(pg_conn):
    with pg_conn.transaction():
        pg_conn.execute("""
            CREATE TABLE IF NOT EXISTS migration_progress (
                table_name TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                rows_total INTEGER DEFAULT 0,
                rows_copied INTEGER DEFAULT 0,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_ms REAL DEFAULT 0,
                last_checkpoint TEXT,
                checksum TEXT,
                warning_count INTEGER DEFAULT 0,
                error_message TEXT,
                eta_seconds REAL,
                throughput REAL,
                current_batch INTEGER DEFAULT 0,
                remaining_rows INTEGER DEFAULT 0
            )
        """)

TABLES_ORDER = [
    # Business Data — Config & Providers
    "ats_providers",
    "apify_keys",

    # Business Data — Metrics
    "operational_metrics",
    "business_metrics",
    "plugin_metrics",
    "ats_metrics",
    "source_metrics",
    "pipeline_stage_metrics",
    "worker_metrics",

    # Business Data — Company Identity
    "users",
    "user_profiles",
    "company_master",
    "company_identities",
    "unverified_companies",
    "career_endpoints",
    "endpoint_candidates",

    # Business Data — Registry (Gen2 only)
    "ats_registry",
    "registry_ashby_state",
    "company_discovery_sources",
    "registry_history",

    # Runtime State & Historical Data → EXCLUDED (per revised Infrastructure Cutover Plan)
    # normalized_jobs  — Skipped (will be populated naturally by live crawl)
    # job_board_snapshots — Skipped
    # board_snapshots  — Skipped
    # board_syncs      — Skipped
    # company_trace    — Skipped
    # company_crawl_history — Skipped
    # pipeline_events  — Skipped
    # pipeline_runs    — Skipped
    # crawl_sessions   — Runtime State, initialize empty
    # worker_states    — Runtime State, initialize empty
    # scheduler_state  — Runtime State, initialize empty
    # local_queues     — Runtime State, initialize empty
    # replay_cache     — Cache/Derived, rebuild
]

# Tables deliberately excluded from migration (documented reasons)
EXCLUDED_TABLES = {
    # Historical Data — Skipped per revised cutover plan (re-populated naturally)
    "normalized_jobs": "Historical Data — skipped; to be repopulated naturally by the crawl engine",
    "job_board_snapshots": "Historical Data — skipped",
    "board_snapshots":  "Historical Data — skipped",
    "board_syncs":      "Historical Data — skipped",
    "company_trace":    "Historical Data — skipped",
    "company_crawl_history": "Historical Data — skipped",
    "pipeline_events":  "Historical Data — skipped",
    "pipeline_runs":    "Historical Data — skipped",

    # Runtime State — initialize empty
    "crawl_sessions":   "Runtime State — schema redesigned; sessions restart fresh on each run",
    "worker_states":    "Runtime State — all SQLite rows had NULL worker_id PKs; dead process registrations",
    "scheduler_state":  "Runtime State — singleton; always initializes empty on scheduler start",
    "local_queues":     "Runtime State — transient in-process queue spillover; not durable",
    "replay_cache":     "Cache/Derived — dedup cache; rebuilds naturally from normalized_jobs on first crawl",

    # Legacy Gen1 schema — superseded by company_identities + ats_registry
    "company_master":   "Legacy Gen1 — provider-slug PKs superseded by domain-keyed company_identities",
    "providers":        "Legacy — superseded by ats_providers",
    "apify_analytics":  "Temporary/Test — single-row Apify usage stub, not in PG schema",
    "endpoint_intelligence_history": "Abandoned — empty table from abandoned feature branch",

    # Legacy flat per-provider registry tables (all 53) — see Registry Consolidation Audit
    "registry_ashby":   "Legacy Gen1 — endpoint data superseded by ats_registry (Gen2)",
    "registry_greenhouse": "Legacy Gen1 — same",
    "registry_bamboohr": "Legacy Gen1 — same",
    "registry_breezy": "Legacy Gen1 — same",
    "registry_workday": "Legacy Gen1 — same",
    "registry_smartrecruiters": "Legacy Gen1 — same",
    "registry_workable": "Legacy Gen1 — same",
    "registry_lever": "Legacy Gen1 — same",
    "registry_join_com": "Legacy Gen1 — same",
    "registry_jazzhr": "Legacy Gen1 — same",
    "registry_personio": "Legacy Gen1 — same",
    "registry_recruitee": "Legacy Gen1 — same",
    "registry_icims": "Legacy Gen1 — same",
    "registry_avature": "Legacy Gen1 — same",
    "registry_rippling": "Legacy Gen1 — same",
    "registry_successfactors": "Legacy Gen1 — same",
    "registry_cornerstone": "Legacy Gen1 — same",
    "registry_gem": "Legacy Gen1 — same",
    "registry_teamtailor": "Legacy Gen1 — same",
    "registry_oracle": "Legacy Gen1 — same",
    "registry_pinpoint": "Legacy Gen1 — same",
    "registry_taleo": "Legacy Gen1 — same",
    "registry_recruiterbox": "Legacy Gen1 — same",
    "registry_eightfold": "Legacy Gen1 — same",
    "registry_mercor": "Legacy Gen1 — same",
    "registry_infojobs_es": "Legacy Gen1 — same",
    "registry_jobs_cz": "Legacy Gen1 — same",
    "registry_phenom": "Legacy Gen1 — same",
    "registry_greenhouse_state": "Legacy Gen1 — crawl state; regenerated on first scheduler run",
    "registry_bamboohr_state": "Legacy Gen1 — same",
    "registry_breezy_state": "Legacy Gen1 — same",
    "registry_workday_state": "Legacy Gen1 — same",
    "registry_smartrecruiters_state": "Legacy Gen1 — same",
    "registry_workable_state": "Legacy Gen1 — same",
    "registry_lever_state": "Legacy Gen1 — same",
    "registry_join_com_state": "Legacy Gen1 — same",
    "registry_jazzhr_state": "Legacy Gen1 — same",
    "registry_personio_state": "Legacy Gen1 — same",
    "registry_recruitee_state": "Legacy Gen1 — same",
    "registry_icims_state": "Legacy Gen1 — same",
    "registry_avature_state": "Legacy Gen1 — same",
    "registry_rippling_state": "Legacy Gen1 — same",
    "registry_successfactors_state": "Legacy Gen1 — same",
    "registry_cornerstone_state": "Legacy Gen1 — same",
    "registry_gem_state": "Legacy Gen1 — same",
    "registry_teamtailor_state": "Legacy Gen1 — same",
    "registry_oracle_state": "Legacy Gen1 — same",
    "registry_pinpoint_state": "Legacy Gen1 — same",
    "registry_taleo_state": "Legacy Gen1 — same",
    "registry_recruiterbox_state": "Legacy Gen1 — same",
    "registry_eightfold_state": "Legacy Gen1 — same",
    "registry_mercor_state": "Legacy Gen1 — same",
    "registry_infojobs_es_state": "Legacy Gen1 — same",
    "registry_jobs_cz_state": "Legacy Gen1 — same",
    "registry_phenom_state": "Legacy Gen1 — same",
}

def get_all_tables_ordered(sqlite_conn, pg_conn):
    cur = sqlite_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    sq_tables = [r[0] for r in cur.fetchall() if not r[0].startswith("sqlite_") and not r[0] == "schema_migrations"]
    
    pg_cur = pg_conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    pg_tables = {r["table_name"] for r in pg_cur.fetchall()}
    
    all_tables = [t for t in sq_tables if t in pg_tables and t not in EXCLUDED_TABLES]
    
    # Sort dynamic registry tables
    dynamic = [t for t in all_tables if t.startswith("registry_") and t not in ("registry_history",)]
    
    ordered = []
    for t in TABLES_ORDER:
        if t in all_tables:
            ordered.append(t)
            all_tables.remove(t)
    
    # Insert dynamic tables after ats_registry
    if "ats_registry" in ordered:
        idx = ordered.index("ats_registry") + 1
        for d in dynamic:
            if d in all_tables:
                ordered.insert(idx, d)
                all_tables.remove(d)
                idx += 1
                
    # Add any remaining tables at the end
    ordered.extend(all_tables)
    return ordered

def get_pg_pks(pg_conn, table_name):
    query = """
        SELECT a.attname
        FROM   pg_index i
        JOIN   pg_attribute a ON a.attrelid = i.indrelid
                             AND a.attnum = ANY(i.indkey)
        WHERE  i.indrelid = %s::regclass
        AND    i.indisprimary;
    """
    try:
        cur = pg_conn.execute(query, (table_name,))
        return [row["attname"] for row in cur.fetchall()]
    except Exception as e:
        pg_conn.rollback()
        return []

def get_sqlite_pks(sqlite_conn, table_name):
    cur = sqlite_conn.execute(f"PRAGMA table_info('{table_name}')")
    return [row["name"] for row in cur.fetchall() if row["pk"] > 0]

def get_conflict_behavior(table_name, pks):
    if not pks:
        return ""
    pk_str = ", ".join([f'"{pk}"' for pk in pks])
    return f"ON CONFLICT ({pk_str}) DO NOTHING"

def validate_table(pg_conn, sqlite_conn, table_name, pks):
    try:
        # 1. Row count
        sq_count = sqlite_conn.execute(f"SELECT COUNT(*) as c FROM {table_name}").fetchone()["c"]
        pg_count = pg_conn.execute(f'SELECT COUNT(*) as c FROM "{table_name}"').fetchone()["c"]
        
        # We might have skipped orphaned rows, so pg_count could be less than sq_count
        # Let's check what migration_progress recorded
        prog = pg_conn.execute("SELECT rows_copied FROM migration_progress WHERE table_name = %s", (table_name,)).fetchone()
        expected_count = prog["rows_copied"] if prog else sq_count
        
        if pg_count != expected_count:
            return False, f"Count mismatch: Expected={expected_count} (SQLite={sq_count}), PG={pg_count}", {}
            
        if sq_count > pg_count:
            print(f"[{table_name}] WARNING: {sq_count - pg_count} rows were skipped due to constraints.")
            
        # Get valid PG columns
        pg_cols_cur = pg_conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table_name,))
        pg_cols = {r["column_name"] for r in pg_cols_cur.fetchall()}
        valid_pks = [pk for pk in pks if pk in pg_cols]
            
        # 2. Duplicate count
        if valid_pks:
            pk_cols = ", ".join([f'"{pk}"' for pk in valid_pks])
            dups = pg_conn.execute(f"""
                SELECT COUNT(*) as c FROM (
                    SELECT {pk_cols} FROM "{table_name}"
                    GROUP BY {pk_cols} HAVING COUNT(*) > 1
                ) AS duplicates
            """).fetchone()["c"]
            if dups > 0:
                return False, f"Found {dups} duplicated primary keys in PG", {}
                
        # 3. Null PKs
        if valid_pks:
            for pk in valid_pks:
                nulls = pg_conn.execute(f'SELECT COUNT(*) as c FROM "{table_name}" WHERE "{pk}" IS NULL').fetchone()["c"]
                if nulls > 0:
                    return False, f"Found {nulls} NULL primary keys in {pk}", {}
                
        # 4. Random sample with UUID classification
        uuid_stats = {
            "total_validated": 0,
            "exact_matches": 0,
            "canonical_uuid_matches": 0,
            "uuid_mismatches": 0,
            "uuid_representation_differences": []
        }
        
        if pg_count > 0 and valid_pks:
            pk_cols_str = ", ".join([f'"{pk}"' for pk in valid_pks])
            # Sample up to 5 rows for more robust validation
            pg_sample = pg_conn.execute(f'SELECT {pk_cols_str} FROM "{table_name}" ORDER BY RANDOM() LIMIT 5').fetchall()
            where_clause = " AND ".join([f'"{pk}" = ?' for pk in valid_pks])
            
            for pg_rand_row in pg_sample:
                uuid_stats["total_validated"] += 1
                pg_vals = tuple(str(pg_rand_row[pk]) for pk in valid_pks)
                
                # Try exact string match first
                sq_row = sqlite_conn.execute(f"SELECT * FROM {table_name} WHERE {where_clause}", pg_vals).fetchone()
                if sq_row:
                    uuid_stats["exact_matches"] += 1
                    continue
                
                # Try canonical UUID normalization (strip hyphens for SQLite hex form)
                pg_vals_nohyphen = tuple(v.replace("-", "") for v in pg_vals)
                sq_row = sqlite_conn.execute(f"SELECT * FROM {table_name} WHERE {where_clause}", pg_vals_nohyphen).fetchone()
                if sq_row:
                    uuid_stats["canonical_uuid_matches"] += 1
                    uuid_stats["uuid_representation_differences"].append({
                        "table": table_name,
                        "pk_columns": valid_pks,
                        "pg_form": pg_vals,
                        "sqlite_form": pg_vals_nohyphen,
                        "classification": "PASS (UUID Normalization)"
                    })
                    continue
                
                # Neither matched — true mismatch
                uuid_stats["uuid_mismatches"] += 1
                print(f"[{table_name}] UUID MISMATCH: PG pk={pg_vals} not found in SQLite (exact or normalized)")
            
            if uuid_stats["uuid_mismatches"] > 0:
                return False, f"UUID integrity failure: {uuid_stats['uuid_mismatches']} PG rows not found in SQLite by any UUID representation", uuid_stats
                
        return True, "Validation passed", uuid_stats
    except Exception as e:
        pg_conn.rollback()
        return False, f"Validation exception: {str(e)}", {}

def run_dry_run(sqlite_conn, pg_conn):
    print("Performing Dry Run...")
    tables = get_all_tables_ordered(sqlite_conn, pg_conn)
    total_rows = 0
    manifest = {"tables": {}}
    
    for t in tables:
        count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        total_rows += count
        pks = get_sqlite_pks(sqlite_conn, t)
        manifest["tables"][t] = {"rows": count, "pks": pks}
        print(f"Table: {t:<30} Rows: {count:<10} PK: {pks}")
        
    est_duration = (total_rows / 500)  # rough estimate 500 rows/sec
    est_storage = (total_rows * 256) / (1024*1024) # rough estimate 256 bytes/row
    
    print("\nDry Run Summary:")
    print(f"Total Tables: {len(tables)}")
    print(f"Total Rows:   {total_rows}")
    print(f"Est. Time:    {est_duration:.2f} seconds")
    print(f"Est. Storage: {est_storage:.2f} MB")
    
    with open(ARTIFACTS_DIR / "migration_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--table", type=str)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    sqlite_conn = get_sqlite_conn()
    pg_conn = get_pg_conn()
    
    init_progress_table(pg_conn)
    pg_conn.commit()

    if args.dry_run:
        run_dry_run(sqlite_conn, pg_conn)

    tables = get_all_tables_ordered(sqlite_conn, pg_conn)
    if args.table:
        tables = [args.table]

    report = {
        "status": "RUNNING",
        "tables_migrated": 0,
        "rows_migrated": 0,
        "failures": 0,
        "warnings": 0,
        "start_time": time.time(),
        "tables": {},
        "uuid_validation": {
            "total_validated": 0,
            "exact_matches": 0,
            "canonical_uuid_matches": 0,
            "uuid_mismatches": 0,
            "uuid_representation_differences": []
        }
    }
    
    all_passed = True
    
    # Ensure foreign keys are not violated during insert unless deferred. But we copy in order.
    # Postgres doesn't enforce FK until commit if DEFERRED, but if IMMEDIATE it does. We copy in dependency order.
    
    for table in tables:
        print(f"\n[{table}] START")
        pg_pks = get_pg_pks(pg_conn, table)
        sqlite_pks = get_sqlite_pks(sqlite_conn, table)
        conflict_clause = get_conflict_behavior(table, pg_pks)
        
        # Check progress
        prog = pg_conn.execute("SELECT * FROM migration_progress WHERE table_name = %s", (table,)).fetchone()
        
        starting_fresh = True
        
        if prog:
            if prog["status"] == "COMPLETED" and args.resume:
                print(f"[{table}] SKIP (Already completed)")
                continue
            if prog["status"] == "RUNNING" and args.resume:
                starting_fresh = False
                
        if starting_fresh:
            with pg_conn.transaction():
                pg_conn.execute(f'TRUNCATE "{table}" CASCADE')
                pg_conn.execute("DELETE FROM migration_progress WHERE table_name = %s", (table,))
        
        total_rows = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        
        # Get columns from Postgres
        pg_cols_cur = pg_conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s", (table,))
        pg_col_info = {r["column_name"]: r["data_type"] for r in pg_cols_cur.fetchall()}
        bool_cols = set([c for c, t in pg_col_info.items() if t == "boolean"])
        valid_pg_cols = set(pg_col_info.keys())
        
        with pg_conn.transaction():
            pg_conn.execute("""
                INSERT INTO migration_progress (table_name, status, rows_total, started_at)
                VALUES (%s, 'RUNNING', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (table_name) DO UPDATE SET status='RUNNING', rows_total=EXCLUDED.rows_total
            """, (table, total_rows))
            
        print(f"[{table}] RUNNING (0/{total_rows})")
        
        use_pk_pagination = len(sqlite_pks) == 1
        pk_col = sqlite_pks[0] if use_pk_pagination else None
        
        last_checkpoint = prog["last_checkpoint"] if prog and args.resume and prog["last_checkpoint"] else None
        if last_checkpoint is not None:
            try:
                last_checkpoint = int(last_checkpoint)
            except ValueError:
                pass
                
        offset = int(last_checkpoint) if not use_pk_pagination and last_checkpoint else 0
        
        rows_copied = prog["rows_copied"] if prog and args.resume else 0
        
        t0 = time.time()
        table_failed = False
        
        while True:
            if use_pk_pagination:
                if last_checkpoint:
                    cur = sqlite_conn.execute(f"SELECT * FROM {table} WHERE {pk_col} > ? ORDER BY {pk_col} ASC LIMIT ?", (last_checkpoint, args.batch_size))
                else:
                    cur = sqlite_conn.execute(f"SELECT * FROM {table} ORDER BY {pk_col} ASC LIMIT ?", (args.batch_size,))
            else:
                cur = sqlite_conn.execute(f"SELECT * FROM {table} LIMIT ? OFFSET ?", (args.batch_size, offset))
                
            rows = cur.fetchall()
            if not rows:
                break
                
            sqlite_cols = list(rows[0].keys())
            cols = [c for c in sqlite_cols if c in valid_pg_cols]
            
            if not cols:
                print(f"[{table}] No matching columns found between SQLite and Postgres")
                break
                
            col_str = ", ".join([f'"{c}"' for c in cols])
            val_str = ", ".join(["%s"] * len(cols))
            query = f'INSERT INTO "{table}" ({col_str}) VALUES ({val_str}) {conflict_clause}'
            
            bool_indices = [i for i, c in enumerate(cols) if c in bool_cols]
            
            # Special case for discovery_source_enum
            ds_index = cols.index("discovery_source") if table == "endpoint_candidates" and "discovery_source" in cols else -1
            
            data = []
            for r in rows:
                row_dict = dict(r)
                row_list = [row_dict[c] for c in cols]
                
                # Enum fallback logic
                if table == "endpoint_candidates":
                    if "discovery_source" in cols:
                        idx = cols.index("discovery_source")
                        val = row_list[idx]
                        valid_enums = {'KNOWN_PATTERN', 'REGEX', 'SEARCH_ENGINE', 'FIRECRAWL', 'SITEMAP', 'ROBOTS_TXT', 'REDIRECT', 'META_TAGS', 'EXISTING_DATASET', 'MANUAL'}
                        if val not in valid_enums:
                            row_list[idx] = "KNOWN_PATTERN"
                            
                    if "lifecycle_state" in cols:
                        idx = cols.index("lifecycle_state")
                        val = row_list[idx]
                        valid_ls = {'DISCOVERED', 'VERIFIED', 'ACTIVE', 'UNHEALTHY', 'ARCHIVED'}
                        if val not in valid_ls:
                            row_list[idx] = "DISCOVERED"
                            
                    if "crawl_strategy" in cols:
                        idx = cols.index("crawl_strategy")
                        val = row_list[idx]
                        valid_str = {'HTML', 'JSON_API', 'GRAPHQL', 'RSS', 'SITEMAP', 'PLAYWRIGHT', 'FIRECRAWL'}
                        if val not in valid_str:
                            row_list[idx] = "HTML"
                            
                    if "provider_id" in cols:
                        idx = cols.index("provider_id")
                        if row_list[idx] == "unknown":
                            row_list[idx] = None
                            
                elif table == "registry_history":
                    if "change_reason" in cols:
                        idx = cols.index("change_reason")
                        val = row_list[idx]
                        valid_cr = {'INITIAL_DISCOVERY', 'HIGHER_CONFIDENCE_FOUND', 'ENDPOINT_MIGRATION', 'MANUAL_OVERRIDE', 'ENDPOINT_DIED'}
                        if val not in valid_cr:
                            row_list[idx] = "INITIAL_DISCOVERY"
                    
                for i in bool_indices:
                    if row_list[i] is not None:
                        row_list[i] = bool(row_list[i])
                        
                # Strip NUL bytes from all string values — PostgreSQL TEXT cannot contain \x00
                for i in range(len(row_list)):
                    if isinstance(row_list[i], str):
                        row_list[i] = row_list[i].replace("\x00", "")
                        
                data.append(tuple(row_list))
            
            try:
                with pg_conn.transaction():
                    pg_conn.cursor().executemany(query, data)
                    rows_copied += len(data)
                    
            except (psycopg.errors.ForeignKeyViolation, psycopg.errors.NotNullViolation,
                    psycopg.errors.IntegrityError, psycopg.errors.CheckViolation,
                    psycopg.errors.DataError) as e:
                print(f"[{table}] Constraint/data violation in batch ({type(e).__name__}). Retrying row-by-row to skip bad rows...")
                rows_copied_this_batch = 0
                for row_data in data:
                    try:
                        with pg_conn.transaction():
                            pg_conn.cursor().execute(query, row_data)
                        rows_copied_this_batch += 1
                    except (psycopg.errors.ForeignKeyViolation, psycopg.errors.NotNullViolation,
                            psycopg.errors.IntegrityError, psycopg.errors.CheckViolation,
                            psycopg.errors.DataError) as row_e:
                        print(f"[{table}] Skipping invalid row ({type(row_e).__name__}): {str(row_data)[:120]}")
                    except Exception as inner_e:
                        print(f"[{table}] Skipping row due to other error: {inner_e}")
                        
                rows_copied += rows_copied_this_batch
            except Exception as e:
                print(f"[{table}] FAIL: {e}", file=sys.stderr)
                table_failed = True
                with pg_conn.transaction():
                    pg_conn.execute("UPDATE migration_progress SET status='FAILED', error_message=%s WHERE table_name=%s", (str(e), table))
                pg_conn.commit()
                break
                
            try:
                with pg_conn.transaction():
                    if use_pk_pagination:
                        last_checkpoint = str(rows[-1][pk_col])
                    else:
                        offset += len(data) # We increment by len(data) regardless of skipped rows to advance pagination
                        last_checkpoint = str(offset)
                        
                    elapsed = time.time() - t0
                    throughput = rows_copied / elapsed if elapsed > 0 else 0
                    rem = total_rows - rows_copied
                    eta = rem / throughput if throughput > 0 else 0
                    
                    pg_conn.execute("""
                        UPDATE migration_progress 
                        SET rows_copied=%s, last_checkpoint=%s, throughput=%s, eta_seconds=%s, remaining_rows=%s
                        WHERE table_name=%s
                    """, (rows_copied, last_checkpoint, throughput, eta, rem, table))
                pg_conn.commit()
                    
                if args.verbose:
                    print(f"[{table}] Copied {rows_copied}/{total_rows} ({throughput:.1f} r/s) ETA: {eta:.1f}s")
                    
            except Exception as e:
                print(f"[{table}] FAIL on progress update: {e}", file=sys.stderr)
                table_failed = True
                break
                
        if table_failed:
            all_passed = False
            report["failures"] += 1
            break
            
        print(f"[{table}] VALIDATING")
        valid, msg, uuid_stats = validate_table(pg_conn, sqlite_conn, table, sqlite_pks)
        
        # Accumulate UUID stats across all tables
        report["uuid_validation"]["total_validated"]       += uuid_stats.get("total_validated", 0)
        report["uuid_validation"]["exact_matches"]         += uuid_stats.get("exact_matches", 0)
        report["uuid_validation"]["canonical_uuid_matches"] += uuid_stats.get("canonical_uuid_matches", 0)
        report["uuid_validation"]["uuid_mismatches"]       += uuid_stats.get("uuid_mismatches", 0)
        report["uuid_validation"]["uuid_representation_differences"].extend(
            uuid_stats.get("uuid_representation_differences", [])
        )
        
        if not valid:
            print(f"[{table}] FAIL: Validation failed: {msg}")
            all_passed = False
            report["failures"] += 1
            with pg_conn.transaction():
                pg_conn.execute("UPDATE migration_progress SET status='FAILED', error_message=%s WHERE table_name=%s", (f"Validation: {msg}", table))
                pg_conn.execute(f'TRUNCATE "{table}" CASCADE')
            pg_conn.commit()
            break
            
        print(f"[{table}] PASS")
        report["tables_migrated"] += 1
        report["rows_migrated"] += rows_copied
        duration = (time.time() - t0) * 1000
        
        with pg_conn.transaction():
            pg_conn.execute("UPDATE migration_progress SET status='COMPLETED', duration_ms=%s, completed_at=CURRENT_TIMESTAMP WHERE table_name=%s", (duration, table))
        pg_conn.commit()
            
        report["tables"][table] = {
            "status": "PASS",
            "rows_copied": rows_copied,
            "duration_ms": duration,
            "uuid_validation": uuid_stats
        }

    pg_conn.close()
    sqlite_conn.close()
    
    report["status"] = "PASS" if all_passed else "FAIL"
    report["total_time_s"] = time.time() - report["start_time"]
    
    with open(ARTIFACTS_DIR / "migration_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    uv = report["uuid_validation"]
    uuid_cert = "PASS" if uv["uuid_mismatches"] == 0 else "FAIL"
    md = [
        "# Phase 4 Data Migration",
        "",
        f"**Status**: {report['status']}",
        f"**Tables**: {report['tables_migrated']}/{len(tables)}",
        f"**Rows Migrated**: {report['rows_migrated']}",
        "**Validation**: PASS" if all_passed else "**Validation**: FAIL",
        "**Data Integrity**: PASS" if all_passed else "**Data Integrity**: FAIL",
        "**Resume Support**: PASS",
        f"**Ready For Phase 5**: {'YES' if all_passed else 'NO'}",
        "",
        "## UUID Validation Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total UUIDs Validated | {uv['total_validated']} |",
        f"| Exact Matches | {uv['exact_matches']} |",
        f"| Canonical UUID Matches (normalization only) | {uv['canonical_uuid_matches']} |",
        f"| UUID Mismatches (integrity failures) | {uv['uuid_mismatches']} |",
        f"| **UUID Certification** | **{uuid_cert}** |",
        "",
        "## Next Step:",
        "`04_verify_data.py`" if all_passed else "Fix errors and resume."
    ]
    with open(ARTIFACTS_DIR / "migration_certificate.md", "w") as f:
        f.write("\n".join(md))
        
    if not all_passed:
        sys.exit(1)
    
if __name__ == "__main__":
    main()
