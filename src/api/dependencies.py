import sqlite3

def get_db():
    conn = sqlite3.connect("data/crm.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
