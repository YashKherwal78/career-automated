from typing import Optional, Any, List, Dict
import time
from src.core.repositories.base import BaseRepository

class DashboardRepository(BaseRepository):
    def _q(self, conn, sql, params=None):
        r = conn.execute(sql, params or []).fetchone()
        return dict(r) if r else {}

    def _ql(self, conn, sql, params=None):
        return [dict(r) for r in conn.execute(sql, params or []).fetchall()]
        
    def get_health_check(self, tx: Optional[Any] = None) -> Dict[str, Any]:
        conn = tx if tx else self.get_connection()
        try:
            cnt = self._q(conn, "SELECT COUNT(*) cnt FROM normalized_jobs")["cnt"]
            
            # DB Info
            is_pg = False
            if hasattr(conn, 'dialect'):
                is_pg = conn.dialect.__class__.__name__ == "PostgreSQLAdapter"
                
            schema_version = "unknown"
            try:
                schema_version = self._q(conn, "SELECT version FROM schema_version ORDER BY id DESC LIMIT 1").get("version", "unknown")
            except:
                pass
                
            return {
                "status": "ok", 
                "jobs": cnt, 
                "ts": int(time.time()),
                "database": "PostgreSQL" if is_pg else "SQLite",
                "schema_version": schema_version
            }
        finally:
            if not tx:
                conn.close()

    def get_pipeline_metrics(self, tx: Optional[Any] = None) -> Dict[str, Any]:
        conn = tx if tx else self.get_connection()
        try:
            now = time.time()
            if hasattr(conn, 'dialect'):
                p = conn.dialect.placeholder()
            else:
                p = "?"

            # General funnel stats
            funnel = {
                "companies_discovered": self._q(conn, "SELECT COUNT(*) cnt FROM company_identities")["cnt"],
                "ats_registry_total": self._q(conn, "SELECT COUNT(*) cnt FROM ats_registry")["cnt"],
                "ats_registry_active": self._q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'ACTIVE'")["cnt"],
                "ats_registry_needs_review": self._q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'NEEDS_REVIEW'")["cnt"],
                "ats_registry_retired": self._q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'RETIRED'")["cnt"],
                "companies_crawled": self._q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE last_successful_crawl IS NOT NULL")["cnt"],
                "companies_never_crawled": self._q(conn, "SELECT COUNT(*) cnt FROM ats_registry WHERE status = 'ACTIVE' AND last_successful_crawl IS NULL")["cnt"],
                "jobs_total": self._q(conn, "SELECT COUNT(*) cnt FROM normalized_jobs")["cnt"],
                "jobs_active": self._q(conn, "SELECT COUNT(*) cnt FROM normalized_jobs WHERE status = 'ACTIVE'")["cnt"],
            }

            # Discovered time-based stats
            funnel["jobs_last_1h"] = self._q(conn, f"SELECT COUNT(*) cnt FROM normalized_jobs WHERE normalized_at > {p}", [now - 3600])["cnt"]
            funnel["jobs_last_24h"] = self._q(conn, f"SELECT COUNT(*) cnt FROM normalized_jobs WHERE normalized_at > {p}", [now - 86400])["cnt"]
            funnel["jobs_last_7d"] = self._q(conn, f"SELECT COUNT(*) cnt FROM normalized_jobs WHERE normalized_at > {p}", [now - 604800])["cnt"]

            # Crawl throughput rates
            jobs_15m = self._q(conn, f"SELECT COUNT(*) cnt FROM normalized_jobs WHERE normalized_at > {p}", [now - 900])["cnt"]
            funnel["crawl_rate_jobs_per_minute"] = round(jobs_15m / 15.0, 2)
            
            jobs_1m = self._q(conn, f"SELECT COUNT(*) cnt FROM normalized_jobs WHERE normalized_at > {p}", [now - 60])["cnt"]
            funnel["db_writes_per_minute"] = jobs_1m

            # Worker states
            workers = []
            try:
                workers = self._ql(conn, "SELECT * FROM worker_states ORDER BY heartbeat DESC LIMIT 20")
            except Exception:
                pass

            active_crawlers_count = 0
            active_workers_count = 0
            for w in workers:
                # Heartbeat within last 90 seconds is considered active
                if now - w.get("heartbeat", 0.0) < 90.0:
                    active_workers_count += 1
                    if "crawler" in w.get("worker_name", "").lower():
                        active_crawlers_count += 1

            funnel["active_crawlers"] = active_crawlers_count
            funnel["active_workers"] = active_workers_count

            # Worker performance metrics (failed crawls, success rate, avg latency)
            try:
                metrics_summary = self._q(conn, "SELECT SUM(processed) as total_proc, SUM(failed) as total_fail, AVG(avg_latency) as mean_lat FROM worker_metrics")
                total_p = metrics_summary.get("total_proc") or 0
                total_f = metrics_summary.get("total_fail") or 0
                funnel["failed_crawls"] = total_f
                funnel["avg_crawl_latency_ms"] = round(metrics_summary.get("mean_lat") or 0.0, 1)
                if total_p + total_f > 0:
                    funnel["success_rate"] = round((total_p / (total_p + total_f)) * 100, 2)
                else:
                    funnel["success_rate"] = 100.0
            except Exception:
                funnel["failed_crawls"] = 0
                funnel["avg_crawl_latency_ms"] = 0.0
                funnel["success_rate"] = 100.0

            # Queue stats
            queues = []
            from src.runtime.postgres.connection import USE_POSTGRES
            if USE_POSTGRES:
                from src.runtime.redis.queue_manager import QueueManager
                try:
                    res_q = [
                        {"queue_name": "discovery_queue", "status": "QUEUED", "cnt": QueueManager.size("discovery_queue")},
                        {"queue_name": "verification_queue", "status": "QUEUED", "cnt": QueueManager.size("verification_queue")},
                        {"queue_name": "crawl_queue", "status": "QUEUED", "cnt": QueueManager.size("crawl_queue")},
                    ]
                    queues = res_q
                except Exception:
                    pass
            else:
                try:
                    queues = self._ql(conn, """
                        SELECT queue_name, status, COUNT(*) cnt
                        FROM local_queues
                        GROUP BY queue_name, status
                        ORDER BY queue_name, status
                    """)
                except Exception:
                    pass

            per_company = self._ql(conn, """
                SELECT n.company_id, a.provider_id as ats_type, COUNT(*) job_count,
                       a.last_successful_crawl, a.failure_count, a.status as ats_status
                FROM normalized_jobs n
                LEFT JOIN ats_registry a ON a.company_id = n.company_id
                GROUP BY n.company_id, a.provider_id, a.last_successful_crawl,
                         a.failure_count, a.status
                ORDER BY job_count DESC
            """)

            return {
                "ts": int(time.time()),
                "funnel": funnel,
                "per_company": per_company,
                "workers": workers,
                "queues": queues,
            }
        finally:
            if not tx:
                conn.close()

    def get_queue_counts(self, tx: Optional[Any] = None) -> Dict[str, int]:
        from src.runtime.postgres.connection import USE_POSTGRES
        if USE_POSTGRES:
            from src.runtime.redis.queue_manager import QueueManager
            try:
                return {
                    "discovery_queue": QueueManager.size("discovery_queue"),
                    "verification_queue": QueueManager.size("verification_queue"),
                    "crawl_queue": QueueManager.size("crawl_queue")
                }
            except Exception:
                return {"discovery_queue": 0, "verification_queue": 0, "crawl_queue": 0}
        
        conn = tx if tx else self.get_connection()
        try:
            res = {"discovery_queue": 0, "verification_queue": 0, "crawl_queue": 0}
            try:
                queues = self._ql(conn, "SELECT queue_name, COUNT(*) cnt FROM local_queues WHERE status = 'QUEUED' GROUP BY queue_name")
                for q in queues:
                    res[q["queue_name"]] = q["cnt"]
            except Exception:
                pass
            return res
        finally:
            if not tx:
                conn.close()

    def get_connector_metrics(self, tx: Optional[Any] = None) -> Dict[str, Any]:
        conn = tx if tx else self.get_connection()
        try:
            ats_stats = self._ql(conn, """
                SELECT
                    provider_id as ats_type,
                    COUNT(*) total_companies,
                    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) active,
                    SUM(CASE WHEN last_successful_crawl IS NOT NULL THEN 1 ELSE 0 END) crawled,
                    SUM(CASE WHEN failure_count > 0 THEN 1 ELSE 0 END) has_failures,
                    AVG(failure_count) avg_failures,
                    MAX(last_successful_crawl) most_recent_crawl
                FROM ats_registry
                GROUP BY provider_id
                ORDER BY total_companies DESC
            """)

            jobs_per_ats = self._ql(conn, """
                SELECT a.provider_id as ats_type, COUNT(*) job_count, COUNT(DISTINCT n.company_id) companies_with_jobs
                FROM normalized_jobs n
                JOIN ats_registry a ON a.company_id = n.company_id
                GROUP BY a.provider_id
                ORDER BY job_count DESC
            """)

            jobs_map = {r["ats_type"]: r for r in jobs_per_ats}

            result = []
            for s in ats_stats:
                ats = s["ats_type"]
                crawl_rate = round(s["crawled"] / s["total_companies"] * 100, 1) if s["total_companies"] else 0
                j = jobs_map.get(ats, {})
                result.append({
                    "ats_type": ats,
                    "total_companies": s["total_companies"],
                    "active": s["active"],
                    "crawled": s["crawled"],
                    "crawl_success_rate_pct": crawl_rate,
                    "avg_failures": round(float(s["avg_failures"] or 0), 2),
                    "job_count": j.get("job_count", 0),
                    "companies_with_jobs": j.get("companies_with_jobs", 0),
                    "avg_jobs_per_company": round(j.get("job_count", 0) / j.get("companies_with_jobs", 1), 1) if j.get("companies_with_jobs") else 0,
                    "most_recent_crawl": s["most_recent_crawl"],
                })

            return {"ts": int(time.time()), "connectors": result}
        finally:
            if not tx:
                conn.close()

    def get_coverage_report(self, top_companies: List[str], tx: Optional[Any] = None) -> Dict[str, Any]:
        conn = tx if tx else self.get_connection()
        try:
            registry = {r["company_id"]: r for r in self._ql(conn, "SELECT company_id, provider_id as ats_type, status FROM ats_registry")}
            job_counts = {r["company_id"]: r["cnt"] for r in self._ql(conn, "SELECT company_id, COUNT(*) cnt FROM normalized_jobs GROUP BY company_id")}

            companies = []
            tracked = 0
            has_jobs = 0
            for cid in top_companies:
                reg = registry.get(cid)
                jobs = job_counts.get(cid, 0)
                if reg:
                    tracked += 1
                if jobs > 0:
                    has_jobs += 1
                companies.append({
                    "company": cid,
                    "in_registry": bool(reg),
                    "ats_type": reg["ats_type"] if reg else None,
                    "ats_status": reg["status"] if reg else None,
                    "job_count": jobs,
                    "status": "✅" if jobs > 0 else ("⚠️" if reg else "❌"),
                })

            return {
                "ts": int(time.time()),
                "summary": {
                    "total_checked": len(top_companies),
                    "in_registry": tracked,
                    "has_jobs": has_jobs,
                    "coverage_pct": round(has_jobs / len(top_companies) * 100, 1) if top_companies else 0,
                },
                "companies": companies,
            }
        finally:
            if not tx:
                conn.close()

    def get_tier_distribution(self, tx: Optional[Any] = None) -> Dict[str, Any]:
        conn = tx if tx else self.get_connection()
        try:
            providers = self._ql(conn, "SELECT id, name FROM providers WHERE enabled=1")
            
            tier_counts = {"CRITICAL": 0, "HIGH": 0, "NORMAL": 0, "LOW": 0, "DORMANT": 0}
            total_churn = 0.0
            total_interval = 0
            total_companies = 0
            
            due_now = 0
            waiting = 0
            
            for p in providers:
                pid = p["id"]
                safe_pid = "".join([c if c.isalnum() else '_' for c in pid])
                table = f"registry_{safe_pid}_state"
                
                try:
                    counts = self._ql(conn, f"SELECT crawl_tier, COUNT(*) as cnt FROM {table} GROUP BY crawl_tier")
                    for c in counts:
                        t = c["crawl_tier"]
                        if t in tier_counts:
                            tier_counts[t] += c["cnt"]
                    
                    avg_stats = self._q(conn, f"SELECT SUM(rolling_churn_percent) as sum_churn, SUM(crawl_interval_hours) as sum_interval, COUNT(*) as cnt FROM {table}")
                    if avg_stats and avg_stats["cnt"] > 0:
                        total_churn += avg_stats["sum_churn"] or 0
                        total_interval += avg_stats["sum_interval"] or 0
                        total_companies += avg_stats["cnt"]
                    
                    queues = self._q(conn, f"SELECT SUM(CASE WHEN next_crawl <= CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as due, SUM(CASE WHEN next_crawl > CURRENT_TIMESTAMP THEN 1 ELSE 0 END) as wait FROM {table} WHERE status IN ('QUEUED', 'RETRY')")
                    if queues:
                        due_now += queues["due"] or 0
                        waiting += queues["wait"] or 0
                except Exception:
                    pass
                    
            return {
                "distribution": tier_counts,
                "avg_churn_rate": round(total_churn / total_companies, 4) if total_companies > 0 else 0,
                "avg_interval_hours": round(total_interval / total_companies, 1) if total_companies > 0 else 0,
                "queues": {
                    "due_now": due_now,
                    "waiting": waiting
                }
            }
        finally:
            if not tx:
                conn.close()

    def get_job_sync_history(self, company_id: str, limit: int = 50, tx: Optional[Any] = None) -> List[Dict[str, Any]]:
        conn = tx if tx else self.get_connection()
        try:
            if hasattr(conn, 'dialect'):
                p = conn.dialect.placeholder()
            else:
                p = "?"
            return self._ql(conn, f"SELECT * FROM company_crawl_history WHERE company_id = {p} ORDER BY crawl_time DESC LIMIT {p}", (company_id, limit))
        finally:
            if not tx:
                conn.close()
