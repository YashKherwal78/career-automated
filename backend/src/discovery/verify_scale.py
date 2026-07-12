import sqlite3
import json

DB_PATH = 'data/crm.db'

def fetch_metrics():
    print("=== END-TO-END PRODUCTION VALIDATION METRICS ===")
    
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        # 1. Queue Health
        print("\n[QUEUE HEALTH]")
        c.execute("SELECT crawl_status, COUNT(*) FROM company_crawl_queue GROUP BY crawl_status")
        for row in c.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
        # 2. End-to-End Pipeline Counts
        print("\n[PIPELINE VALIDATION]")
        c.execute("SELECT COUNT(*) FROM company_crawl_queue")
        print(f"  Discovered & Queued: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM company_crawl_queue WHERE crawl_status = 'DONE'")
        print(f"  Processed by Scheduler & Adapter: {c.fetchone()[0]}")
        c.execute("SELECT COUNT(*) FROM canonical_job_store WHERE provider = 'workday'")
        parsed = c.fetchone()[0]
        print(f"  Successfully Parsed & Stored: {parsed}")
        
        c.execute("SELECT COUNT(DISTINCT fingerprint) FROM canonical_job_store WHERE provider = 'workday'")
        unique_urls = c.fetchone()[0]
        duplicate_rate = 100 - (unique_urls / max(parsed, 1) * 100) if parsed > 0 else 0
        print(f"  Duplicate Canonical Jobs: {duplicate_rate:.1f}%")
        

            
        print("\n[ADAPTER ERRORS & FAILURES]")
        c.execute("SELECT crawl_status, COUNT(*) FROM company_crawl_queue WHERE crawl_status = 'ERROR' OR crawl_status = 'FAILED'")
        for row in c.fetchall():
            print(f"  Queue Failures ({row[0]}): {row[1]}")
            
        print("\nDone.")

if __name__ == '__main__':
    fetch_metrics()
