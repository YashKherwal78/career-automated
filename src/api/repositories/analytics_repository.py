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

    def get_pipeline_kpis(self):
        c = self.db.cursor()
        c.execute("SELECT count(*) FROM company_identities")
        companies_count = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM career_endpoints")
        endpoints_count = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM ats_registry WHERE status = 'ACTIVE'")
        verified_count = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM normalized_jobs WHERE status = 'ACTIVE'")
        jobs_count = c.fetchone()[0]

        workers = {
            "discovery": "Stopped",
            "verification": "Stopped",
            "crawler": "Stopped",
            "cleanup": "Stopped",
            "failures": 0
        }
        try:
            c.execute("SELECT worker_name, status, failures FROM worker_states")
            for row in c.fetchall():
                name = row[0].lower()
                status = row[1]
                failures = row[2]
                if "discovery" in name:
                    workers["discovery"] = status
                elif "verification" in name:
                    workers["verification"] = status
                elif "crawler" in name:
                    workers["crawler"] = status
                elif "cleanup" in name:
                    workers["cleanup"] = status
                workers["failures"] += failures
        except Exception:
            pass
        
        dq, vq, cq = 0, 0, 0
        try:
            c.execute("SELECT count(*) FROM local_queues WHERE queue_name = 'discovery_queue' AND status = 'QUEUED'")
            dq = c.fetchone()[0]
            c.execute("SELECT count(*) FROM local_queues WHERE queue_name = 'verification_queue' AND status = 'QUEUED'")
            vq = c.fetchone()[0]
            c.execute("SELECT count(*) FROM local_queues WHERE queue_name = 'crawl_queue' AND status = 'QUEUED'")
            cq = c.fetchone()[0]
        except Exception:
            pass

        return {
            "companies": companies_count,
            "endpoints": endpoints_count,
            "verified": verified_count,
            "jobs": jobs_count,
            "workers": {
                "discovery": workers["discovery"],
                "verification": workers["verification"],
                "crawler": workers["crawler"],
                "cleanup": workers["cleanup"],
                "retry_queue": dq + vq + cq,
                "failures": workers["failures"]
            }
        }
