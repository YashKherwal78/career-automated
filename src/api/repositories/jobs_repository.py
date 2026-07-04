import sqlite3
import json

class JobRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_jobs(self, page: int = 1, page_size: int = 50, provider: str = None, company: str = None, status: str = 'ACTIVE', min_score: float = None):
        c = self.db.cursor()
        query = """
            SELECT i.canonical_name, n.job_id, n.title, n.job_score, n.provider, n.score_breakdown, 
                   n.match_score, n.priority_score, n.scoring_confidence, n.recommendation_reason, n.application_status
            FROM normalized_jobs n
            JOIN company_identities i ON n.company_id = i.company_id
            WHERE n.status = ?
        """
        params = [status]
        
        if provider:
            query += " AND n.provider = ?"
            params.append(provider)
        if company:
            query += " AND i.canonical_name LIKE ?"
            params.append(f"%{company}%")
        if min_score is not None:
            query += " AND n.job_score >= ?"
            params.append(min_score)
            
        query += " ORDER BY n.job_score DESC LIMIT ? OFFSET ?"
        params.extend([page_size, (page - 1) * page_size])
        
        c.execute(query, params)
        jobs = [dict(row) for row in c.fetchall()]
        
        for j in jobs:
            try: j["score_breakdown"] = json.loads(j["score_breakdown"] or "[]")
            except: j["score_breakdown"] = []
            
        return jobs
