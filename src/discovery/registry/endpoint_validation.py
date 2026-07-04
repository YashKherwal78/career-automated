import sqlite3
import hashlib
from typing import List, Dict, Any

class NormalizedJob:
    def __init__(self, company_id: str, title: str, location: str, employment_type: str, 
                 remote: bool, department: str, description: str, apply_url: str, 
                 connector: str, ats_id: str):
        self.company_id = company_id
        self.title = title
        self.location = location
        self.employment_type = employment_type
        self.remote = remote
        self.department = department
        self.description = description
        self.apply_url = apply_url
        self.connector = connector
        self.ats_id = ats_id
        
        # SHA256(company + title + location + employment + ATS ID)
        fp_str = f"{company_id}|{title}|{location}|{employment_type}|{ats_id}".lower()
        self.fingerprint = hashlib.sha256(fp_str.encode()).hexdigest()

class EndpointValidationEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def _ensure_normalized_jobs_table(self, c):
        c.execute('''
            CREATE TABLE IF NOT EXISTS normalized_jobs (
                fingerprint TEXT PRIMARY KEY,
                company_id TEXT,
                title TEXT,
                location TEXT,
                employment_type TEXT,
                remote BOOLEAN,
                department TEXT,
                description TEXT,
                apply_url TEXT,
                connector TEXT,
                ats_id TEXT,
                discovered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
    def _mock_fetch_jobs(self, endpoint_url: str, company_id: str, ats_provider: str) -> List[NormalizedJob]:
        """Mock implementation of fetching from ATS."""
        # For POC, simulate returning jobs for Greenhouse, 0 jobs for Lever
        if "greenhouse" in ats_provider.lower():
            return [
                NormalizedJob(company_id, "Product Analyst", "Bangalore", "Full Time", False, "Product", 
                              "Mock description", f"{endpoint_url}/apply/123", ats_provider, "123")
            ]
        return []

    def validate_endpoints(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        self._ensure_normalized_jobs_table(c)
        
        # Fetch DISCOVERED_ENDPOINT
        c.execute('''
            SELECT endpoint_id, company_id, career_url, ats_provider 
            FROM career_endpoints 
            WHERE status = 'DISCOVERED_ENDPOINT' OR status = 'VERIFYING'
        ''')
        targets = c.fetchall()
        
        verified_count = 0
        jobs_found = 0
        
        for eid, cid, url, ats in targets:
            c.execute("UPDATE career_endpoints SET status = 'VERIFYING' WHERE endpoint_id = ?", (eid,))
            conn.commit()
            
            try:
                jobs = self._mock_fetch_jobs(url, cid, ats)
                
                # Insert normalized jobs with fingerprint
                for job in jobs:
                    c.execute('''
                        INSERT INTO normalized_jobs (fingerprint, company_id, title, location, 
                                                    employment_type, remote, department, description, 
                                                    apply_url, connector, ats_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(fingerprint) DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP
                    ''', (job.fingerprint, job.company_id, job.title, job.location, 
                          job.employment_type, job.remote, job.department, job.description, 
                          job.apply_url, job.connector, job.ats_id))
                    jobs_found += 1
                
                # Mark as verified regardless of job count
                c.execute('''
                    UPDATE career_endpoints 
                    SET status = 'VERIFIED', confidence = 0.99, health_status = 'HEALTHY', 
                        last_verified_at = CURRENT_TIMESTAMP 
                    WHERE endpoint_id = ?
                ''', (eid,))
                verified_count += 1
                
            except Exception as e:
                # Store failure
                c.execute('''
                    UPDATE career_endpoints 
                    SET status = 'FAILED', health_status = 'BROKEN', failure_reason = ? 
                    WHERE endpoint_id = ?
                ''', (str(e), eid))
                
        conn.commit()
        conn.close()
        
        return len(targets), verified_count, jobs_found
