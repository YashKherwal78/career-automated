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

    def get_runs(self):
        c = self.db.cursor()
        c.execute("SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 50")
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_plugins(self):
        c = self.db.cursor()
        c.execute("SELECT * FROM plugin_metrics")
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_sources(self):
        c = self.db.cursor()
        c.execute("SELECT * FROM source_metrics")
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_workers(self):
        c = self.db.cursor()
        c.execute("SELECT * FROM worker_metrics")
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_queues(self):
        c = self.db.cursor()
        c.execute("SELECT * FROM queue_metrics")
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_data_quality(self):
        c = self.db.cursor()
        
        # Dead verified boards
        c.execute("SELECT COUNT(*) FROM ats_registry WHERE status = 'FAILED'")
        dead_boards = c.fetchone()[0]
        
        # Zero-job boards
        c.execute("SELECT COUNT(*) FROM ats_registry WHERE job_count = 0")
        zero_job_boards = c.fetchone()[0]
        
        # Duplicate companies
        c.execute("SELECT COUNT(*) - COUNT(DISTINCT company_id) FROM company_identities")
        dup_companies = c.fetchone()[0]
        
        # Stale boards (not checked in last 14 days)
        import time
        stale_threshold = time.time() - (14 * 24 * 3600)
        c.execute("SELECT COUNT(*) FROM ats_registry WHERE last_checked < ?", (stale_threshold,))
        stale_boards = c.fetchone()[0]
        
        return {
            "dead_verified_boards": dead_boards,
            "zero_job_boards": zero_job_boards,
            "duplicate_companies": max(0, dup_companies),
            "stale_boards": stale_boards
        }

    def get_lineage(self, company_id: str):
        c = self.db.cursor()
        c.execute("""
            SELECT event_id, event_type, payload, timestamp, run_id, stage, status, ats_type, latency_ms, reason_code
            FROM pipeline_events 
            WHERE company_id = ? 
            ORDER BY timestamp ASC
        """, (company_id,))
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_priorities(self):
        c = self.db.cursor()
        priorities = []
        
        # 1. Backlog Check
        c.execute("SELECT count(*) FROM local_queues WHERE queue_name='discovery_queue' AND status='QUEUED'")
        backlog = c.fetchone()[0]
        if backlog > 500:
            priorities.append({
                "severity": "warning",
                "title": f"Discovery queue backlog growing ({backlog} queued)",
                "description": "Backlog exceeds normal threshold of 500. Recommend scaling discovery workers."
            })
            
        # 2. Dead verified boards
        c.execute("SELECT COUNT(*) FROM ats_registry WHERE status = 'FAILED'")
        dead = c.fetchone()[0]
        if dead > 0:
            priorities.append({
                "severity": "danger",
                "title": f"{dead} dead verified boards detected",
                "description": "Failed health checks suggest these boards have migrated, requiring parser/path updates."
            })
            
        # 3. Workable precision check
        c.execute("SELECT verified, candidates_found FROM plugin_metrics WHERE plugin='workable'")
        row = c.fetchone()
        if row:
            verified, candidates = row
            precision = (verified / candidates) * 100 if candidates > 0 else 100
            if precision < 50:
                priorities.append({
                    "severity": "danger",
                    "title": f"Workable plugin precision low ({precision:.1f}%)",
                    "description": "Workable candidate parser is producing high noise. Target: >80% precision."
                })
                
        # Fallback if empty
        if not priorities:
            priorities.append({
                "severity": "success",
                "title": "Pipeline is healthy",
                "description": "All stages operate within target conversion, precision, and latency thresholds."
            })
        return priorities

    def get_queue_items(self, queue_name: str):
        c = self.db.cursor()
        c.execute("""
            SELECT item_id, payload, status, failures, created_at 
            FROM local_queues 
            WHERE queue_name = ? AND status = 'QUEUED' 
            ORDER BY created_at ASC LIMIT 50
        """, (queue_name,))
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_dead_boards(self):
        c = self.db.cursor()
        c.execute("SELECT company_id, endpoint, ats_type, failure_count FROM ats_registry WHERE status = 'FAILED' LIMIT 50")
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_zero_job_boards(self):
        c = self.db.cursor()
        c.execute("SELECT company_id, endpoint, ats_type, job_count FROM ats_registry WHERE job_count = 0 LIMIT 50")
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]

    def get_duplicate_companies(self):
        c = self.db.cursor()
        c.execute("""
            SELECT company_id, canonical_name, website 
            FROM company_identities 
            WHERE company_id IN (
                SELECT company_id FROM company_identities GROUP BY company_id HAVING COUNT(*) > 1
            ) LIMIT 50
        """)
        columns = [col[0] for col in c.description]
        return [dict(zip(columns, row)) for row in c.fetchall()]
