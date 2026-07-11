from src.system.logger import setup_logger
logger = setup_logger('database')
import sqlite3
import pandas as pd
from src.config.config import Config
import os

DB_PATH = Config.DATABASE_PATH

def get_db_connection():
    # Use read-only connection URI to prevent locks
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_table(table_name: str) -> pd.DataFrame:
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except Exception as e:
        logger.info(f"Error reading {table_name}: {e}")
        return pd.DataFrame()

def fetch_query(query: str, params=()) -> pd.DataFrame:
    try:
        conn = get_db_connection()
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df
    except Exception as e:
        logger.info(f"Error executing query: {e}")
        return pd.DataFrame()

def get_latest_heartbeats() -> pd.DataFrame:
    query = """
    SELECT worker_name, status, started_at, finished_at, execution_time, items_processed
    FROM worker_heartbeats
    WHERE (worker_name, timestamp) IN (
        SELECT worker_name, MAX(timestamp) 
        FROM worker_heartbeats 
        GROUP BY worker_name
    )
    """
    return fetch_query(query)
