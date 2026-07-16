import sys, sqlite3, os
sys.path.append('.')
from src.api.db import get_connection

conn = get_connection()
providers = [f[:-4] for f in os.listdir('research/ats-scrapers-main/ats-companies') if f.endswith('.csv')]
for p in providers:
    safe_p = "".join([c if c.isalnum() else '_' for c in p])
    try:
        conn.execute(f"ALTER TABLE registry_{safe_p}_state ADD COLUMN previous_jobs INTEGER DEFAULT 0")
        conn.execute(f"ALTER TABLE registry_{safe_p}_state ADD COLUMN current_jobs INTEGER DEFAULT 0")
        conn.execute(f"ALTER TABLE registry_{safe_p}_state ADD COLUMN job_delta INTEGER DEFAULT 0")
    except Exception as e:
        print(f"{safe_p}: {e}")
conn.commit()
conn.close()
