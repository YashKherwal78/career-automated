import sqlite3

class AnalyticsRepository:
    def __init__(self, db: sqlite3.Connection):
        self.db = db

    def get_funnel_kpis(self):
        c = self.db.cursor()
        c.execute("SELECT count(DISTINCT company_id) FROM company_identities")
        total_companies = c.fetchone()[0]
        
        c.execute("SELECT count(DISTINCT endpoint_id) FROM career_endpoints WHERE status = 'VERIFIED'")
        verified_ats = c.fetchone()[0]
        
        c.execute("SELECT count(job_id) FROM normalized_jobs WHERE status = 'ACTIVE'")
        active_jobs = c.fetchone()[0]
        
        c.execute("SELECT count(application_id) FROM applications")
        applications = c.fetchone()[0]
        
        return {
            "companies": total_companies,
            "verified_ats": verified_ats,
            "live_jobs": active_jobs,
            "applications_sent": applications,
            "recruiters_found": 0,
            "referrals_requested": 0,
            "interviews": 0,
            "offers": 0
        }
