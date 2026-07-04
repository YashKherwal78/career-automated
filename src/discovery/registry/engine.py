import sqlite3
import pandas as pd
import uuid
import re
from typing import List, Set

class DiscoveryEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def _normalize_company_name(self, name: str) -> str:
        """Removes legal entities for deduplication."""
        name = str(name).strip().lower()
        name = re.sub(r'\b(inc|llc|ltd|pvt|private|limited|corp|corporation)\b\.?', '', name)
        name = re.sub(r'[^a-z0-9]', '', name)
        return name

    def ingest_sources(self, iit_excel_path: str, extra_excel_path: str = None) -> int:
        """Ingests companies from multiple sources, deduplicates, and incrementally updates registry."""
        raw_companies = []
        
        # 1. IIT List
        try:
            df = pd.read_excel(iit_excel_path)
            for name in df['Company Name'].dropna().tolist():
                raw_companies.append((name.strip(), "IIT Placement List"))
        except Exception as e:
            print(f"Warning: Failed to load IIT list: {e}")
            
        # 2. Extra List (Placeholder)
        if extra_excel_path:
            try:
                df_extra = pd.read_excel(extra_excel_path)
                for name in df_extra['Company Name'].dropna().tolist():
                    raw_companies.append((name.strip(), "Extra Company List"))
            except Exception as e:
                print(f"Warning: Failed to load Extra list: {e}")
                
        # 3. Curated Startup Additions
        curated = ["Razorpay", "CRED", "Groww", "PhonePe", "Zepto", "Meesho", "Swiggy", "Zomato"]
        for c in curated:
            raw_companies.append((c, "Curated Startups"))

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        added_count = 0
        for name, source in raw_companies:
            canonical = self._normalize_company_name(name)
            if not canonical:
                continue
                
            # Check if canonical name exists in aliases or canonical_name
            c.execute("SELECT company_id FROM company_identities WHERE canonical_name = ?", (canonical,))
            row = c.fetchone()
            
            if not row:
                # Insert new CompanyIdentity
                new_uuid = str(uuid.uuid4())
                domain = f"{canonical}.unknown" # Placeholder until Slug Discovery finds real domain
                
                # We use a try-except because the domain might accidentally collide in our placeholder
                try:
                    c.execute('''
                        INSERT INTO company_identities (company_id, domain, canonical_name, legal_name)
                        VALUES (?, ?, ?, ?)
                    ''', (new_uuid, domain, canonical, name))
                    
                    # Also insert into CandidateCompanies queue for Slug Discovery
                    # We will create a candidate queue table or just use a status flag in a discovery table
                    # For now, let's ensure the table exists
                    c.execute('''
                        CREATE TABLE IF NOT EXISTS candidate_companies (
                            company_id TEXT PRIMARY KEY,
                            discovery_source TEXT,
                            status TEXT DEFAULT 'PENDING_SLUG_DISCOVERY',
                            FOREIGN KEY(company_id) REFERENCES company_identities(company_id)
                        )
                    ''')
                    
                    c.execute('''
                        INSERT INTO candidate_companies (company_id, discovery_source)
                        VALUES (?, ?)
                    ''', (new_uuid, source))
                    
                    added_count += 1
                except sqlite3.IntegrityError:
                    pass # Domain collision, skip
            else:
                # Already exists. We preserve history by not overwriting, 
                # but we could append the new discovery source to a provenance log.
                pass
                
        conn.commit()
        conn.close()
        return added_count
