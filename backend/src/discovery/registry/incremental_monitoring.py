import sqlite3
import hashlib
from typing import List, Dict, Any

class JobLifecycleManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    def _compute_content_hash(self, title: str, description: str, location: str, employment_type: str) -> str:
        fp_str = f"{title}|{description}|{location}|{employment_type}".lower()
        return hashlib.sha256(fp_str.encode()).hexdigest()
        
    def process_polled_jobs(self, endpoint_id: str, company_id: str, connector: str, raw_jobs: List[Dict[str, Any]]):
        """Processes an array of raw jobs, computes hashes, and updates lifecycle states."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        current_fingerprints = set()
        
        for rj in raw_jobs:
            title = rj.get('title', '')
            location = rj.get('location', '')
            employment_type = rj.get('employment_type', '')
            ats_id = rj.get('ats_id', '')
            description = rj.get('description', '')
            apply_url = rj.get('apply_url', '')
            department = rj.get('department', '')
            remote = rj.get('remote', False)
            
            # 1. Job Fingerprinting (Identity)
            fp_str = f"{company_id}|{title}|{location}|{employment_type}|{ats_id}".lower()
            fingerprint = hashlib.sha256(fp_str.encode()).hexdigest()
            current_fingerprints.add(fingerprint)
            
            # 2. Content Hashing (Change Detection)
            content_hash = self._compute_content_hash(title, description, location, employment_type)
            
            c.execute("SELECT content_hash, status FROM normalized_jobs WHERE fingerprint = ?", (fingerprint,))
            row = c.fetchone()
            
            if not row:
                # NEW JOB
                c.execute('''
                    INSERT INTO normalized_jobs (fingerprint, content_hash, company_id, title, location, 
                                                employment_type, remote, department, description, 
                                                apply_url, connector, ats_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW')
                ''', (fingerprint, content_hash, company_id, title, location, 
                      employment_type, remote, department, description, apply_url, connector, ats_id))
            else:
                old_hash = row[0]
                status = row[1]
                if old_hash != content_hash:
                    # UPDATED JOB (Content changed, requires JIE re-parse)
                    c.execute('''
                        UPDATE normalized_jobs 
                        SET content_hash = ?, description = ?, status = 'UPDATED', last_seen_at = CURRENT_TIMESTAMP 
                        WHERE fingerprint = ?
                    ''', (content_hash, description, fingerprint))
                else:
                    # UNCHANGED JOB (Skip JIE, just update last seen)
                    new_status = 'ACTIVE' if status == 'NEW' else status
                    c.execute('''
                        UPDATE normalized_jobs 
                        SET last_seen_at = CURRENT_TIMESTAMP, status = ?
                        WHERE fingerprint = ?
                    ''', (new_status, fingerprint))
                    
        # 3. Detect CLOSED Jobs
        if current_fingerprints:
            placeholders = ','.join(['?'] * len(current_fingerprints))
            c.execute(f'''
                UPDATE normalized_jobs 
                SET status = 'CLOSED' 
                WHERE company_id = ? AND fingerprint NOT IN ({placeholders}) AND status != 'CLOSED'
            ''', [company_id] + list(current_fingerprints))
            
        conn.commit()
        conn.close()
