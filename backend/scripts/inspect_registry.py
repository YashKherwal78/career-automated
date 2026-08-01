import sys
sys.path.append('.')
from src.api.db import get_connection

def main():
    conn = get_connection()
    try:
        cur = conn.execute("SELECT company_id, provider_id, status, endpoint FROM ats_registry")
        rows = cur.fetchall()
        for r in rows:
            print(dict(r) if hasattr(r, "keys") else r)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
