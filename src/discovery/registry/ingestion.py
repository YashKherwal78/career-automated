import os
import sqlite3
import pandas as pd
import uuid
import re
from typing import List, Set

class IngestionEngine:
    def __init__(self, db_path: str, source_folder: str):
        self.db_path = db_path
        self.source_folder = source_folder
        
    def _normalize_company_name(self, name: str) -> str:
        """Removes legal entities for deduplication."""
        name = str(name).strip().lower()
        name = re.sub(r'\b(inc|llc|ltd|pvt|private|limited|corp|corporation)\b\.?', '', name)
        name = re.sub(r'[^a-z0-9]', '', name)
        return name
        
    def _ensure_schema(self, c):
        c.execute('''
            CREATE TABLE IF NOT EXISTS candidate_companies (
                company_id TEXT PRIMARY KEY,
                discovery_source TEXT,
                status TEXT DEFAULT 'DISCOVERED',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
            )
        ''')

    def ingest_all(self) -> int:
        """Scans the source folder and ingests all CSVs and Excels."""
        if not os.path.exists(self.source_folder):
            return 0
            
        raw_companies = []
        for file in os.listdir(self.source_folder):
            file_path = os.path.join(self.source_folder, file)
            source_name = file
            try:
                if file.endswith('.csv'):
                    df = pd.read_csv(file_path)
                elif file.endswith('.xlsx'):
                    df = pd.read_excel(file_path)
                else:
                    continue
                    
                # Look for a common column name like "Company Name" or "company"
                col = None
                for c in df.columns:
                    if 'company' in c.lower() or 'name' in c.lower():
                        col = c
                        break
                        
                if col:
                    for name in df[col].dropna().tolist():
                        raw_companies.append((name.strip(), source_name))
            except Exception as e:
                print(f"Warning: Failed to load {file}: {e}")

        if not raw_companies:
            return 0

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        self._ensure_schema(c)
        
        added_count = 0
        for name, source in raw_companies:
            canonical = self._normalize_company_name(name)
            if not canonical:
                continue
                
            c.execute("SELECT company_id FROM company_identities WHERE canonical_name = ?", (canonical,))
            row = c.fetchone()
            
            if not row:
                new_uuid = str(uuid.uuid4())
                domain = f"{canonical}.unknown"
                try:
                    c.execute('''
                        INSERT INTO company_identities (company_id, domain, canonical_name, legal_name)
                        VALUES (?, ?, ?, ?)
                    ''', (new_uuid, domain, canonical, name))
                    
                    c.execute('''
                        INSERT INTO candidate_companies (company_id, discovery_source)
                        VALUES (?, ?)
                    ''', (new_uuid, source))
                    added_count += 1
                except sqlite3.IntegrityError:
                    pass
                    
        conn.commit()
        conn.close()
        return added_count
