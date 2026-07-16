from dotenv import load_dotenv; load_dotenv(".env")
import psycopg, os, psycopg.rows
conn = psycopg.connect(os.getenv("DATABASE_URL"), row_factory=psycopg.rows.dict_row)

for tname in ["registry_ashby_state", "ats_registry"]:
    print(f"\n=== PG {tname} schema ===")
    cols = conn.execute(
        "SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position",
        (tname,)
    ).fetchall()
    for c in cols:
        print(f"  {c['column_name']}: {c['data_type']}")

print("\n=== PG registry_ashby_state sample row ===")
row = conn.execute("SELECT * FROM registry_ashby_state LIMIT 1").fetchone()
if row:
    for k, v in row.items():
        print(f"  {k}: {v}")
