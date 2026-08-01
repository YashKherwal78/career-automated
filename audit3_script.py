import os
import psycopg
import json
import random

def run_audit():
    conn = psycopg.connect(os.environ["OPERATIONAL_DATABASE_URL"])
    from psycopg.rows import dict_row
    cur = conn.cursor(row_factory=dict_row)
    data = {}

    # 1. Next Check Distribution (Relative to NOW)
    # How many companies become due every hour from now?
    cur.execute("""
        SELECT 
            SUM(CASE WHEN next_check_at_tz <= NOW() THEN 1 ELSE 0 END) as already_due,
            SUM(CASE WHEN next_check_at_tz > NOW() AND next_check_at_tz <= NOW() + interval '1 hour' THEN 1 ELSE 0 END) as due_in_0_1h,
            SUM(CASE WHEN next_check_at_tz > NOW() + interval '1 hour' AND next_check_at_tz <= NOW() + interval '2 hours' THEN 1 ELSE 0 END) as due_in_1_2h,
            SUM(CASE WHEN next_check_at_tz > NOW() + interval '2 hours' AND next_check_at_tz <= NOW() + interval '3 hours' THEN 1 ELSE 0 END) as due_in_2_3h,
            SUM(CASE WHEN next_check_at_tz > NOW() + interval '3 hours' AND next_check_at_tz <= NOW() + interval '4 hours' THEN 1 ELSE 0 END) as due_in_3_4h,
            SUM(CASE WHEN next_check_at_tz > NOW() + interval '4 hours' AND next_check_at_tz <= NOW() + interval '6 hours' THEN 1 ELSE 0 END) as due_in_4_6h,
            SUM(CASE WHEN next_check_at_tz > NOW() + interval '6 hours' AND next_check_at_tz <= NOW() + interval '12 hours' THEN 1 ELSE 0 END) as due_in_6_12h,
            SUM(CASE WHEN next_check_at_tz > NOW() + interval '12 hours' AND next_check_at_tz <= NOW() + interval '24 hours' THEN 1 ELSE 0 END) as due_in_12_24h,
            SUM(CASE WHEN next_check_at_tz > NOW() + interval '24 hours' THEN 1 ELSE 0 END) as due_after_24h
        FROM ats_registry 
        WHERE next_check_at_tz IS NOT NULL
    """)
    data['due_distribution'] = cur.fetchone()

    # 2. Delta Distribution (next_check_at_tz - last_successful_crawl)
    cur.execute("""
        SELECT 
            MIN(EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl) as min_delta,
            MAX(EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl) as max_delta,
            AVG(EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl) as avg_delta,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY (EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl)) as median_delta,
            percentile_cont(0.9) WITHIN GROUP (ORDER BY (EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl)) as p90_delta,
            percentile_cont(0.99) WITHIN GROUP (ORDER BY (EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl)) as p99_delta
        FROM ats_registry 
        WHERE last_successful_crawl > 0 AND next_check_at_tz IS NOT NULL
    """)
    data['delta_distribution'] = cur.fetchone()

    # 3. Provider Cadence (Delta grouped by provider)
    cur.execute("""
        SELECT 
            provider_id, 
            AVG(EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl) as avg_delta,
            COUNT(*) as companies
        FROM ats_registry 
        WHERE last_successful_crawl > 0 AND next_check_at_tz IS NOT NULL
        GROUP BY provider_id
        ORDER BY companies DESC
        LIMIT 10
    """)
    data['provider_cadence'] = cur.fetchall()

    # 4. 100 Random Companies (completed_at -> next_check_at -> delta)
    cur.execute("""
        SELECT 
            company_id,
            provider_id,
            last_successful_crawl as completed_epoch,
            EXTRACT(EPOCH FROM next_check_at_tz) as next_check_epoch,
            EXTRACT(EPOCH FROM next_check_at_tz) - last_successful_crawl as delta_seconds
        FROM ats_registry 
        WHERE last_successful_crawl > 0 AND next_check_at_tz IS NOT NULL
        ORDER BY RANDOM() LIMIT 100
    """)
    data['random_100'] = cur.fetchall()
    
    # Custom Decimal Encoder
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            from decimal import Decimal
            import datetime
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime.timedelta):
                return obj.total_seconds()
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super(DecimalEncoder, self).default(obj)
            
    print(json.dumps(data, cls=DecimalEncoder))

if __name__ == "__main__":
    run_audit()
