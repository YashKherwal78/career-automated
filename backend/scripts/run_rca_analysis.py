import sqlite3
import json
import time
import datetime
from collections import defaultdict

DB_PATH = "backend/data/crm.db"

def run_query(conn, query, params=()):
    try:
        cursor = conn.execute(query, params)
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        return []
    except Exception as e:
        return [{"error": str(e), "query": query}]

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get today's start epoch in local timezone (as done earlier)
    now = datetime.datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    yesterday_start = today_start - 86400
    
    results = {}
    
    # Stage 1: Scheduler Throughput (companies due vs reserved vs crawled)
    # Using ats_registry:
    # Due: next_check_at <= now
    # Reserved: reserved_until > now
    # Crawled today: last_successful_crawl >= today_start
    # Active: status = 'ACTIVE'
    
    q1 = """
    SELECT 
        provider_id,
        count(*) as total_active,
        sum(case when next_check_at <= ? then 1 else 0 end) as due,
        sum(case when reserved_until > ? then 1 else 0 end) as reserved,
        sum(case when last_successful_crawl >= ? then 1 else 0 end) as crawled_today,
        sum(case when crawl_status = 'FAILED' then 1 else 0 end) as failed
    FROM ats_registry
    WHERE status = 'ACTIVE'
    GROUP BY provider_id
    """
    results['stage_1_throughput'] = run_query(conn, q1, (now.timestamp(), now.timestamp(), today_start))
    
    # Stage 2 & 3 & 9: Crawl Pipeline Waterfall & Provider coverage
    # Using board_syncs
    q2 = """
    SELECT 
        date(started_at, 'unixepoch', 'localtime') as run_date,
        count(*) as syncs,
        sum(case when success = 1 then 1 else 0 end) as successes,
        sum(case when success = 0 then 1 else 0 end) as failures,
        sum(jobs_extracted) as extracted,
        sum(jobs_inserted) as inserted,
        sum(jobs_updated) as updated,
        sum(jobs_archived) as archived
    FROM board_syncs
    WHERE started_at >= ?
    GROUP BY run_date
    ORDER BY run_date DESC
    """
    results['stage_3_waterfall_daily'] = run_query(conn, q2, (today_start - (86400 * 7),))
    
    q2_provider = """
    SELECT 
        provider,
        count(*) as syncs_today,
        sum(case when success = 1 then 1 else 0 end) as successes,
        sum(jobs_extracted) as extracted,
        sum(jobs_inserted) as inserted,
        sum(jobs_updated) as updated,
        sum(jobs_archived) as archived
    FROM board_syncs
    WHERE started_at >= ?
    GROUP BY provider
    """
    # Wait, board_syncs didn't have provider? In an earlier query `board_syncs` failed because no provider column!
    # Ah, let's join ats_registry to board_syncs via board_id (or endpoint)
    # Let's check board_syncs schema first to be safe.
    
    q_schema_syncs = "PRAGMA table_info(board_syncs);"
    results['schema_board_syncs'] = run_query(conn, q_schema_syncs)
    
    # Stage 4: Job Yield Analysis (avg jobs per company)
    q4 = """
    SELECT 
        provider_id,
        count(*) as companies,
        avg(job_count) as avg_jobs,
        max(job_count) as max_jobs,
        sum(case when job_count = 0 then 1 else 0 end) as zero_jobs,
        sum(case when job_count > 0 and job_count <= 5 then 1 else 0 end) as jobs_1_to_5,
        sum(case when job_count > 5 and job_count <= 20 then 1 else 0 end) as jobs_5_to_20,
        sum(case when job_count > 20 and job_count <= 100 then 1 else 0 end) as jobs_20_to_100,
        sum(case when job_count > 100 then 1 else 0 end) as jobs_over_100
    FROM ats_registry
    WHERE status = 'ACTIVE'
    GROUP BY provider_id
    """
    results['stage_4_job_yield'] = run_query(conn, q4)
    
    # Stage 5: Scheduler Fairness (Stale companies)
    q5 = """
    SELECT 
        provider_id,
        min(last_successful_crawl) as oldest_crawl,
        avg(cast(strftime('%s', 'now') as real) - last_successful_crawl) as avg_staleness_seconds,
        sum(case when (cast(strftime('%s', 'now') as real) - last_successful_crawl) > 86400 then 1 else 0 end) as older_than_24h,
        sum(case when (cast(strftime('%s', 'now') as real) - last_successful_crawl) > 259200 then 1 else 0 end) as older_than_3d,
        sum(case when (cast(strftime('%s', 'now') as real) - last_successful_crawl) > 604800 then 1 else 0 end) as older_than_7d
    FROM ats_registry
    WHERE status = 'ACTIVE'
    GROUP BY provider_id
    """
    results['stage_5_fairness'] = run_query(conn, q5)
    
    # Stage 6: Worker Utilization (From board_syncs durations)
    # Using started_at, duration_ms
    q6 = """
    SELECT 
        avg(duration_ms) as avg_duration,
        max(duration_ms) as max_duration,
        min(duration_ms) as min_duration
    FROM board_syncs
    WHERE started_at >= ?
    """
    results['stage_6_worker'] = run_query(conn, q6, (today_start,))
    
    # Let's also check error messages
    q_errors = """
    SELECT error_message, count(*) as count
    FROM board_syncs
    WHERE started_at >= ? AND success = 0
    GROUP BY error_message
    ORDER BY count DESC
    LIMIT 10
    """
    results['errors_today'] = run_query(conn, q_errors, (today_start,))

    with open('analysis_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
