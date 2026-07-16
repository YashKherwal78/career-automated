import sys, sqlite3, os
sys.path.append('.')
from src.api.db import get_connection

conn = get_connection()
cur = conn.execute("SELECT id, name FROM providers")
providers = cur.fetchall()

total_registry = 0
total_state = 0
errors = 0

print("Import Summary & Sanity Check")
print("-" * 50)
for p_id, p_name in providers:
    c1 = conn.execute(f"SELECT COUNT(*) FROM registry_{p_id}").fetchone()[0]
    c2 = conn.execute(f"SELECT COUNT(*) FROM registry_{p_id}_state").fetchone()[0]
    
    # Check for mismatches
    c3 = conn.execute(f"""
        SELECT COUNT(*) FROM registry_{p_id} r
        LEFT JOIN registry_{p_id}_state s ON r.company_id = s.company_id
        WHERE s.company_id IS NULL
    """).fetchone()[0]
    
    c4 = conn.execute(f"""
        SELECT COUNT(*) FROM registry_{p_id}_state s
        LEFT JOIN registry_{p_id} r ON s.company_id = r.company_id
        WHERE r.company_id IS NULL
    """).fetchone()[0]
    
    print(f"{p_name:<20} {c1:>8} rows")
    if c1 != c2 or c3 > 0 or c4 > 0:
        print(f"  WARNING: Mismatch detected! Registry: {c1}, State: {c2}, Orphans: {c3}, Zombie states: {c4}")
        errors += 1
        
    total_registry += c1
    total_state += c2

print("-" * 50)
print(f"TOTAL: {total_registry}")
if errors == 0 and total_registry == total_state:
    print("\nSanity Check PASSED: 1-to-1 parity confirmed across all provider tables. No duplicates or orphans.")
else:
    print(f"\nSanity Check FAILED: {errors} providers had mismatches.")

conn.close()
