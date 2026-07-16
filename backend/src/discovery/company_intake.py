from src.api.db import get_connection
from typing import Dict, Any, List
import sqlite3

class CompanyIntake:
    """
    Company Discovery as a side-effect of Market Search (Pipeline B).
    Extracts companies from raw opportunities and manages Registry insertion/updates.
    """
    def __init__(self, db_path: str = "hrmail.db"):
        self.db_path = db_path
        
    def process_opportunities(self, opportunities: List[Dict[str, Any]], connector_name: str) -> None:
        """
        Extracts companies from opportunities and processes them through the intake pipeline.
        """
        # 1. Extract unique companies from the batch
        candidates = set()
        for opp in opportunities:
            # Apify specific extractions depending on connector
            company_name = str(opp.get("companyName", opp.get("company", opp.get("company_name", "")))).strip()
            if company_name:
                candidates.add(company_name)
                
        # 2. Process each candidate
        for company in candidates:
            self._intake_candidate(company, connector_name)
            
    def _intake_candidate(self, company_name: str, source: str) -> None:
        """
        Checks if company exists. If NO, inserts as P3 NEW.
        (Note: In a full production implementation, this uses robust fuzzy matching or an established schema).
        """
        # Minimal mock implementation for architecture validation
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # 1. Check if exists
            cursor.execute("SELECT id FROM company_intelligence_static WHERE name = ? COLLATE NOCASE", (company_name,))
            row = cursor.fetchone()
            
            if row:
                # YES -> Update signals (e.g. bump confidence)
                # Actual update query would append the source to a sources array/column
                pass
            else:
                # NO -> Insert as P3 / NEW
                cursor.execute(
                    """
                    INSERT INTO company_intelligence_static (name, priority, lifecycle_state) 
                    VALUES (?, 'P3', 'NEW')
                    """,
                    (company_name,)
                )
                conn.commit()
                
        except sqlite3.OperationalError:
            # DB or table might not exist yet in local tests
            pass
        finally:
            conn.close()
