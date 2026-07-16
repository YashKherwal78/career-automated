from src.api.db import get_connection, DATABASE_PATH
from src.core.repositories.manager import RepositoryManager

def get_repos():
    manager = RepositoryManager(DATABASE_PATH)
    yield manager

def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
