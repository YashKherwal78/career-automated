import os
import psycopg
import json

def run_audit():
    conn = psycopg.connect(os.environ["OPERATIONAL_DATABASE_URL"])
    # use row_factory=dict_row to get dicts
    from psycopg.rows import dict_row
    cur = conn.cursor(row_factory=dict_row)
    
    data = {}
    
    # 1. Dataset Integrity
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs")
    total = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs WHERE status = 'ACTIVE'")
    active = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs WHERE status = 'CLOSED'")
    closed = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs WHERE status = 'ARCHIVED'")
    archived = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs WHERE status = 'SOFT_DELETED'")
    soft_deleted = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs WHERE provider IS NULL OR provider = ''")
    missing_provider = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs WHERE company_id IS NULL OR company_id = ''")
    missing_company = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM normalized_jobs WHERE apply_url IS NULL OR apply_url = ''")
    missing_url = cur.fetchone()["count"]
    
    data['integrity'] = {
        'total': total, 'active': active, 'closed': closed, 'archived': archived,
        'soft_deleted': soft_deleted, 'missing_provider': missing_provider,
        'missing_company': missing_company, 'missing_url': missing_url,
    }
    
    # 2. Duplicate Audit
    cur.execute("""
        SELECT SUM(cnt) as count FROM (
            SELECT COUNT(*) as cnt FROM normalized_jobs 
            WHERE provider_job_id IS NOT NULL AND provider_job_id != ''
            GROUP BY company_id, provider_job_id HAVING COUNT(*) > 1
        ) s
    """)
    res = cur.fetchone()
    data['duplicates_provider_job_id'] = res["count"] if res and res["count"] is not None else 0
    
    cur.execute("""
        SELECT SUM(cnt) as count FROM (
            SELECT COUNT(*) as cnt FROM normalized_jobs 
            WHERE apply_url IS NOT NULL AND apply_url != ''
            GROUP BY apply_url HAVING COUNT(*) > 1
        ) s
    """)
    res = cur.fetchone()
    data['duplicates_apply_url'] = res["count"] if res and res["count"] is not None else 0
    
    cur.execute("""
        SELECT SUM(cnt) as count FROM (
            SELECT COUNT(*) as cnt FROM normalized_jobs 
            WHERE title IS NOT NULL AND location IS NOT NULL
            GROUP BY company_id, title, location HAVING COUNT(*) > 1
        ) s
    """)
    res = cur.fetchone()
    data['duplicates_company_title_loc'] = res["count"] if res and res["count"] is not None else 0
    
    cur.execute("""
        SELECT SUM(cnt) as count FROM (
            SELECT COUNT(*) as cnt FROM normalized_jobs 
            WHERE job_hash IS NOT NULL AND job_hash != ''
            GROUP BY job_hash HAVING COUNT(*) > 1
        ) s
    """)
    res = cur.fetchone()
    data['duplicates_job_hash'] = res["count"] if res and res["count"] is not None else 0

    # 3. Provider Distribution
    cur.execute("""
        SELECT 
            a.provider_id,
            COUNT(DISTINCT a.company_id) as total_companies,
            COUNT(DISTINCT CASE WHEN a.status = 'ACTIVE' THEN a.company_id END) as active_companies,
            SUM(a.job_count) as job_count,
            AVG(NULLIF(a.job_count, 0)) as avg_jobs
        FROM ats_registry a
        GROUP BY a.provider_id
        ORDER BY job_count DESC NULLS LAST
    """)
    data['providers'] = cur.fetchall()

    # 4. Company Coverage
    cur.execute("SELECT COUNT(*) as count FROM ats_registry")
    data['company_total'] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM ats_registry WHERE job_count > 0")
    data['company_with_jobs'] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM ats_registry WHERE job_count = 0 OR job_count IS NULL")
    data['company_without_jobs'] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM ats_registry WHERE last_successful_crawl = 0 OR last_successful_crawl IS NULL")
    data['company_never_crawled'] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM ats_registry WHERE lease_token IS NOT NULL AND lease_token != ''")
    data['company_leased'] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM ats_registry WHERE status = 'DISABLED'")
    data['company_disabled'] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM ats_registry WHERE status = 'ARCHIVED'")
    data['company_archived'] = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) as count FROM ats_registry WHERE failure_count > 3")
    data['company_failing'] = cur.fetchone()["count"]

    # 5. Crawl Freshness
    cur.execute("""
        SELECT 
          SUM(CASE WHEN last_successful_crawl > extract(epoch from (now() - interval '1 hour')) THEN 1 ELSE 0 END) as last_1h,
          SUM(CASE WHEN last_successful_crawl > extract(epoch from (now() - interval '6 hours')) THEN 1 ELSE 0 END) as last_6h,
          SUM(CASE WHEN last_successful_crawl > extract(epoch from (now() - interval '12 hours')) THEN 1 ELSE 0 END) as last_12h,
          SUM(CASE WHEN last_successful_crawl > extract(epoch from (now() - interval '24 hours')) THEN 1 ELSE 0 END) as last_24h,
          SUM(CASE WHEN last_successful_crawl > extract(epoch from (now() - interval '3 days')) THEN 1 ELSE 0 END) as last_3d,
          SUM(CASE WHEN last_successful_crawl > extract(epoch from (now() - interval '7 days')) THEN 1 ELSE 0 END) as last_7d,
          SUM(CASE WHEN last_successful_crawl > extract(epoch from (now() - interval '30 days')) THEN 1 ELSE 0 END) as last_30d
        FROM ats_registry
    """)
    data['freshness'] = cur.fetchone()

    # 6. Scheduler Distribution
    cur.execute("""
        SELECT extract(hour from to_timestamp(next_check_at)) as hour_of_day, COUNT(*) as cnt
        FROM ats_registry 
        WHERE next_check_at > 0
        GROUP BY hour_of_day ORDER BY hour_of_day
    """)
    data['scheduler_dist'] = cur.fetchall()

    # 7. Recrawl Interval Audit
    cur.execute("""
        SELECT 
          MIN(extract(epoch from now()) - last_successful_crawl) as min_age,
          AVG(extract(epoch from now()) - last_successful_crawl) as avg_age,
          percentile_cont(0.5) WITHIN GROUP (ORDER BY (extract(epoch from now()) - last_successful_crawl)) as median_age,
          percentile_cont(0.9) WITHIN GROUP (ORDER BY (extract(epoch from now()) - last_successful_crawl)) as p90_age,
          percentile_cont(0.99) WITHIN GROUP (ORDER BY (extract(epoch from now()) - last_successful_crawl)) as p99_age,
          MAX(extract(epoch from now()) - last_successful_crawl) as max_age
        FROM ats_registry 
        WHERE last_successful_crawl > 0
    """)
    data['recrawl_age'] = cur.fetchone()

    # 8. Throughput Audit
    cur.execute("""
        SELECT 
            event_type, 
            COUNT(*) as count,
            AVG(CAST(payload->>'latency_ms' AS FLOAT)) as avg_latency,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY CAST(payload->>'latency_ms' AS FLOAT)) as p50_latency,
            percentile_cont(0.9) WITHIN GROUP (ORDER BY CAST(payload->>'latency_ms' AS FLOAT)) as p90_latency,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY CAST(payload->>'latency_ms' AS FLOAT)) as p99_latency
        FROM outbox_events 
        WHERE occurred_at > (now() - interval '24 hours')
        AND (event_type = 'JobSynced' OR event_type = 'CrawlFailed')
        GROUP BY event_type
    """)
    data['outbox_stats'] = cur.fetchall()

    cur.execute("""
        SELECT 
            SUM(CAST(payload->>'jobs_inserted' AS INTEGER)) as jobs_inserted,
            SUM(CAST(payload->>'jobs_updated' AS INTEGER)) as jobs_updated
        FROM outbox_events
        WHERE occurred_at > (now() - interval '24 hours')
        AND event_type = 'JobSynced'
    """)
    jobs_thr = cur.fetchone()
    data['jobs_throughput'] = jobs_thr if jobs_thr else {}

    # 13. Data Integrity (Jobs/Company distribution)
    cur.execute("""
        SELECT 
            percentile_cont(0.5) WITHIN GROUP (ORDER BY job_count) as median_jobs,
            percentile_cont(0.9) WITHIN GROUP (ORDER BY job_count) as p90_jobs,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY job_count) as p99_jobs,
            MAX(job_count) as max_jobs
        FROM ats_registry WHERE job_count > 0
    """)
    data['job_dist'] = cur.fetchone()
    
    # Custom Decimal Encoder since percentiles return Decimals in psycopg
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            from decimal import Decimal
            import datetime
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime.timedelta):
                return obj.total_seconds()
            return super(DecimalEncoder, self).default(obj)
            
    print(json.dumps(data, cls=DecimalEncoder))

if __name__ == "__main__":
    run_audit()
