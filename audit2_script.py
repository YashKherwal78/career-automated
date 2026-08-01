import os
import psycopg
import json
import random

def run_audit():
    conn = psycopg.connect(os.environ["OPERATIONAL_DATABASE_URL"])
    from psycopg.rows import dict_row
    cur = conn.cursor(row_factory=dict_row)
    data = {}
    
    # 1. State Machine Metrics
    cur.execute("SELECT COUNT(*) as cnt FROM ats_registry WHERE reservation_token IS NULL AND (next_check_at_tz IS NULL OR next_check_at_tz <= NOW())")
    due_unreserved = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM ats_registry WHERE reservation_token IS NULL AND next_check_at_tz > NOW()")
    waiting_unreserved = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM ats_registry WHERE reservation_token IS NOT NULL AND reserved_until_tz > NOW()")
    active_leases = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM ats_registry WHERE reservation_token IS NOT NULL AND reserved_until_tz <= NOW()")
    stale_leases = cur.fetchone()["cnt"]
    
    data['state_machine'] = {
        'DUE_UNRESERVED': due_unreserved,
        'WAITING_UNRESERVED': waiting_unreserved,
        'ACTIVE_LEASES': active_leases,
        'STALE_LEASES': stale_leases
    }

    # 2. Lease Age Histogram (How long ago were the current active/stale leases acquired or when do they expire?)
    # Since we don't have reserved_at, we have reserved_until_tz which is usually +300s.
    cur.execute("""
        SELECT 
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) BETWEEN -300 AND 0 THEN 1 ELSE 0 END) as active_in_future,
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) BETWEEN 0 AND 60 THEN 1 ELSE 0 END) as stale_under_1m,
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) BETWEEN 60 AND 300 THEN 1 ELSE 0 END) as stale_1m_5m,
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) BETWEEN 300 AND 900 THEN 1 ELSE 0 END) as stale_5m_15m,
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) BETWEEN 900 AND 3600 THEN 1 ELSE 0 END) as stale_15m_1h,
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) BETWEEN 3600 AND 21600 THEN 1 ELSE 0 END) as stale_1h_6h,
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) BETWEEN 21600 AND 86400 THEN 1 ELSE 0 END) as stale_6h_24h,
            SUM(CASE WHEN EXTRACT(EPOCH FROM (NOW() - reserved_until_tz)) > 86400 THEN 1 ELSE 0 END) as stale_over_24h
        FROM ats_registry WHERE reservation_token IS NOT NULL
    """)
    data['lease_histogram'] = cur.fetchone()

    # 3. Random Company Trace
    cur.execute("""
        SELECT company_id, provider_id, status, reservation_token, reserved_by, reserved_until_tz, 
               lease_token, lease_epoch, next_check_at_tz, last_successful_crawl, failure_count
        FROM ats_registry 
        ORDER BY RANDOM() LIMIT 1
    """)
    data['random_trace'] = cur.fetchone()
    
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
