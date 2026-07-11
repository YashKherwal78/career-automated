import sqlite3

def get_db():
    conn = sqlite3.connect("data/crm.db", check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
