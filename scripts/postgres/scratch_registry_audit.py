"""
Registry Consolidation Audit Script
Compares every SQLite registry_* table against the PG schema to determine
what data lives where, what overlaps, and what would be lost.
"""
from dotenv import load_dotenv; load_dotenv(".env")
import sqlite3, psycopg, os, psycopg.rows, json

sq_conn = sqlite3.connect("data/crm.db")
sq_conn.row_factory = sqlite3.Row

pg_conn = psycopg.connect(os.getenv("DATABASE_URL"), row_factory=psycopg.rows.dict_row)

# Get all SQLite registry tables
sq_tables = [r[0] for r in sq_conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'registry_%' ORDER BY name"
).fetchall()]

# Get all PG tables
pg_tables = {r["table_name"] for r in pg_conn.execute(
    "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
).fetchall()}

# For every company in each registry table, check if it exists in company_identities (PG)
pg_companies = {r["company_id"] for r in pg_conn.execute("SELECT company_id FROM company_identities").fetchall()}
# Get PG ats_registry company_ids
pg_ats_registry = {r["company_id"] for r in pg_conn.execute("SELECT DISTINCT company_id FROM ats_registry").fetchall()}
# Get PG registry_ashby_state company_ids
pg_ashby_state = {r["company_id"] for r in pg_conn.execute("SELECT company_id FROM registry_ashby_state").fetchall()}

print(f"PG company_identities: {len(pg_companies)} companies")
print(f"PG ats_registry: {len(pg_ats_registry)} companies")
print(f"PG registry_ashby_state: {len(pg_ashby_state)} companies (includes test rows)")
print()

results = []
for t in sq_tables:
    rows = sq_conn.execute(f"SELECT * FROM {t}").fetchall()
    if not rows:
        results.append({
            "table": t, "rows": 0, "provider": t.replace("registry_", "").replace("_state", ""),
            "is_state_table": "_state" in t,
            "in_pg": t in pg_tables,
            "companies_in_pg_identities": 0,
            "companies_NOT_in_pg_identities": 0,
            "companies_in_pg_ats_registry": 0,
            "verdict": "EMPTY — no data loss"
        })
        continue
    
    company_ids = [r["company_id"] for r in rows]
    in_pg_ci = sum(1 for c in company_ids if c in pg_companies)
    not_in_pg_ci = len(company_ids) - in_pg_ci
    in_pg_ats = sum(1 for c in company_ids if c in pg_ats_registry)
    
    provider = t.replace("registry_", "").replace("_state", "")
    is_state = "_state" in t
    in_pg = t in pg_tables
    
    # Sample endpoint from a data table
    sample_endpoint = None
    if not is_state and rows:
        sample_endpoint = rows[0]["endpoint"] if "endpoint" in rows[0].keys() else None
    
    results.append({
        "table": t,
        "rows": len(rows),
        "provider": provider,
        "is_state_table": is_state,
        "in_pg": in_pg,
        "companies_in_pg_identities": in_pg_ci,
        "companies_NOT_in_pg_identities": not_in_pg_ci,
        "pct_in_pg_identities": round(in_pg_ci/len(company_ids)*100, 1),
        "companies_in_pg_ats_registry": in_pg_ats,
        "sample_endpoint": sample_endpoint,
    })

print(json.dumps(results, indent=2))
