import sys
sys.path.append('.')

from src.api.db import get_connection, is_postgres

def get_row_dict(row, cursor):
    if hasattr(row, "keys"):
        return dict(row)
    if isinstance(row, dict):
        return row
    return dict(zip([col[0] for col in cursor.description], row))

def main():
    print(f"Is PostgreSQL: {is_postgres()}")
    conn = get_connection()
    try:
        # 1. Print all tables
        if is_postgres():
            cur = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = [r[0] if isinstance(r, tuple) else r["table_name"] for r in cur.fetchall()]
        else:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] if isinstance(r, tuple) else r["name"] for r in cur.fetchall()]
        print(f"Database tables: {tables}")
        
        # 2. Check migrations
        cur = conn.execute("SELECT version, applied_at FROM schema_migrations ORDER BY version")
        migrations = [get_row_dict(r, cur) for r in cur.fetchall()]
        print(f"Applied migrations: {migrations}")

        # 3. Check providers
        if "providers" in tables:
            cur = conn.execute("SELECT id, name, enabled, current_workers FROM public.providers")
            providers = [get_row_dict(r, cur) for r in cur.fetchall()]
            print(f"Providers: {providers}")
        else:
            print("No 'providers' table found!")

        # 4. Check active companies in ats_registry
        if "ats_registry" in tables:
            cur = conn.execute("SELECT COUNT(*), status FROM public.ats_registry GROUP BY status")
            counts = [get_row_dict(r, cur) for r in cur.fetchall()]
            print(f"ats_registry counts: {counts}")
        else:
            print("No 'ats_registry' table found!")
            
        # 5. Check company_crawl_queue
        if "company_crawl_queue" in tables:
            cur = conn.execute("SELECT COUNT(*), crawl_status FROM public.company_crawl_queue GROUP BY crawl_status")
            q_counts = [get_row_dict(r, cur) for r in cur.fetchall()]
            print(f"company_crawl_queue counts: {q_counts}")
        else:
            print("No 'company_crawl_queue' table found!")

        # 6. Check active workers
        if "worker_states" in tables:
            cur = conn.execute("SELECT * FROM public.worker_states")
            workers = [get_row_dict(r, cur) for r in cur.fetchall()]
            print(f"Active workers: {workers}")
        else:
            print("No 'worker_states' table found!")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Audit failed with error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
