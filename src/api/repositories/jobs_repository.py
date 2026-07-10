import sqlite3
import json

class JobRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_jobs(
        self,
        page: int = 1,
        page_size: int = 50,
        provider: str = None,
        company: str = None,
        status: str = 'ACTIVE',
        min_score: float = None,
        pipeline: str = "A",
        location: str = None,
        remote_type: str = None,
        employment_type: str = None,
        seniority: str = None,
        min_salary: float = None,
        sort_by: str = "newest"
    ):
        c = self.db.cursor()
        
        # We need extra columns for filtering and display (salary, location, remote, posted_at)
        query = """
            SELECT i.canonical_name, n.job_id, n.title, n.job_score, n.provider, n.score_breakdown, 
                   n.match_score, n.priority_score, n.scoring_confidence, n.recommendation_reason, n.application_status,
                   n.location, n.remote_type as remote, n.employment_type, n.salary_min, n.salary_max, n.posted_at, n.apply_url
            FROM normalized_jobs n
            JOIN company_identities i ON n.company_id = i.company_id
            WHERE n.status = ?
        """
        params = [status]

        # Separate Pipeline A (known ATS) vs Pipeline B (external job boards)
        # Pipeline B contains 'linkedin', 'google_jobs', 'wellfound', etc.
        # Pipeline A contains direct ATS names: greenhouse, lever, workday, ashby, smartrecruiters, workable, personio, teamtailor, recruitee, breezy, etc.
        job_board_providers = ["linkedin", "google_jobs", "wellfound", "indeed"]
        if pipeline == "B":
            query += " AND n.provider IN (" + ",".join(["?"] * len(job_board_providers)) + ")"
            params.extend(job_board_providers)
        else:
            query += " AND n.provider NOT IN (" + ",".join(["?"] * len(job_board_providers)) + ")"
            params.extend(job_board_providers)

        if provider:
            query += " AND n.provider = ?"
            params.append(provider)
        if company:
            query += " AND (i.canonical_name LIKE ? OR n.title LIKE ?)"
            params.extend([f"%{company}%", f"%{company}%"])
        if min_score is not None:
            query += " AND n.job_score >= ?"
            params.append(min_score)
        if location:
            query += " AND n.location LIKE ?"
            params.append(f"%{location}%")
        if remote_type:
            query += " AND n.remote_type = ?"
            params.append(remote_type)
        if employment_type:
            query += " AND n.employment_type = ?"
            params.append(employment_type)
        if seniority:
            query += " AND n.description LIKE ?"  # Simple fallback search for experience keyword
            params.append(f"%{seniority}%")
        if min_salary is not None:
            query += " AND (n.salary_max >= ? OR n.salary_min >= ?)"
            params.extend([min_salary, min_salary])

        # Sorting: newest first (continuous live feed default) or highest score first
        if sort_by == "score":
            query += " ORDER BY n.job_score DESC, n.posted_at DESC LIMIT ? OFFSET ?"
        else:
            query += " ORDER BY n.posted_at DESC, n.job_score DESC LIMIT ? OFFSET ?"
            
        params.extend([page_size, (page - 1) * page_size])
        
        c.execute(query, params)
        jobs = [dict(row) for row in c.fetchall()]
        
        for j in jobs:
            try: j["score_breakdown"] = json.loads(j["score_breakdown"] or "[]")
            except: j["score_breakdown"] = []
            
        return jobs

    def get_job(self, job_id: str):
        c = self.db.cursor()
        c.execute("""
            SELECT i.canonical_name, n.job_id, n.title, n.job_score, n.provider, n.score_breakdown, 
                   n.match_score, n.priority_score, n.scoring_confidence, n.recommendation_reason, n.application_status,
                   n.description, n.location, n.remote_type as remote, n.salary_min, n.salary_max, n.apply_url, n.posted_at
            FROM normalized_jobs n
            JOIN company_identities i ON n.company_id = i.company_id
            WHERE n.job_id = ?
        """, (job_id,))
        row = c.fetchone()
        if not row:
            return None
        j = dict(row)
        try: j["score_breakdown"] = json.loads(j["score_breakdown"] or "[]")
        except: j["score_breakdown"] = []
        return j
