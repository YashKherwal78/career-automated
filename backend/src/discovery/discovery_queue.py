from src.api.db import get_connection
import sqlite3
from typing import List, Dict, Any
from src.config.config import Config

class DiscoveryQueue:
    """
    Manages the priority queue for company discovery (P0 -> P1 -> P2 -> P3).
    Ensures we don't scan all 900 companies simultaneously.
    """
    def __init__(self, db_path: str = Config.DATABASE_PATH):
        self.db_path = db_path

    def get_next_batch(self, batch_size: int = 20) -> List[Dict[str, Any]]:
        """
        Fetches the next batch of companies to scan based on priority and lifecycle.
        Prioritizes P0 > P1 > P2 > P3.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # We fetch companies that are 'ACTIVE' or 'NEW' but haven't been scanned recently
        cursor.execute('''
            SELECT * FROM company_intelligence_static 
            ORDER BY 
                CASE priority
                    WHEN 'P0' THEN 1
                    WHEN 'P1' THEN 2
                    WHEN 'P2' THEN 3
                    WHEN 'P3' THEN 4
                    ELSE 5
                END ASC,
                last_updated ASC
            LIMIT ?
        ''', (batch_size,))
        
        companies = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return companies
