import sys, sqlite3
sys.path.append('.')
from src.api.db import get_connection

conn = get_connection()
conn.execute("UPDATE providers SET current_workers=1, min_workers=1")
conn.commit()
conn.close()
print("All providers set to conservative start (1 worker).")
