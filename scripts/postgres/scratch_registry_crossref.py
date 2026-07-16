import sqlite3
conn = sqlite3.connect("data/crm.db")
conn.row_factory = sqlite3.Row

# Check registry_ashby IDs vs company_master 
print("=== registry_ashby sample ===")
for r in conn.execute("SELECT company_id, company_name, endpoint FROM registry_ashby LIMIT 3").fetchall():
    print(dict(r))

print("\n=== company_master schema ===")
print(conn.execute("SELECT sql FROM sqlite_master WHERE name='company_master'").fetchone()[0])

print("\n=== company_master sample ===")
for r in conn.execute("SELECT * FROM company_master LIMIT 3").fetchall():
    print(dict(r))

print("\n=== Does company_master bridge registry IDs? ===")
ashby_ids = [r["company_id"] for r in conn.execute("SELECT company_id FROM registry_ashby LIMIT 20").fetchall()]
cm_ids = {r["company_id"] for r in conn.execute("SELECT company_id FROM company_master").fetchall()}
overlap = [i for i in ashby_ids if i in cm_ids]
print(f"First 20 registry_ashby IDs in company_master: {len(overlap)}")
print(f"Example ashby IDs: {ashby_ids[:5]}")
print(f"Example company_master IDs: {list(cm_ids)[:5]}")

print("\n=== Is company_master the parent of registry_* tables? ===")
total_ashby = {r["company_id"] for r in conn.execute("SELECT company_id FROM registry_ashby").fetchall()}
total_cm = {r["company_id"] for r in conn.execute("SELECT company_id FROM company_master").fetchall()}
print(f"registry_ashby unique IDs: {len(total_ashby)}")
print(f"company_master unique IDs: {len(total_cm)}")
print(f"registry_ashby IDs in company_master: {len(total_ashby & total_cm)}")
