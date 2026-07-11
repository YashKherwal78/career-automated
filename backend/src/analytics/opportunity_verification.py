from src.system.logger import setup_logger
logger = setup_logger('opportunity_verification')
import sqlite3
import requests
import concurrent.futures
from src.config.config import Config
from datetime import datetime

DB_PATH = Config.DATABASE_PATH

def verify_url(url: str) -> tuple:
    """Returns (verification_status, http_status)"""
    if not url or url == '#':
        return ("ERROR", 0)
        
    try:
        # Use a real user-agent to avoid simple blocks
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=5)
        
        status_code = response.status_code
        final_url = response.url
        
        # 404 means the job is gone
        if status_code == 404:
            return ("CLOSED", status_code)
            
        # 403 or 401 means auth error, assume active but log error
        if status_code in [401, 403]:
            return ("ACTIVE (AUTH)", status_code)
            
        # Often ATS redirects to generic careers page when job is closed
        if status_code == 200:
            if url != final_url and ("jobs" not in final_url and "posting" not in final_url):
                # E.g., redirect from lever.co/company/123 to lever.co/company
                return ("CLOSED", status_code)
            return ("ACTIVE", status_code)
            
        return ("ERROR", status_code)
        
    except requests.RequestException:
        return ("ERROR", 0)

def verify_top_opportunities(limit=100):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get top unverified or old-verified jobs
    c.execute("""
        SELECT id, job_url 
        FROM jobs 
        WHERE (verification_status = 'UNVERIFIED' OR last_verified_at < date('now', '-1 day'))
        AND ranking_score > 0
        ORDER BY ranking_score DESC 
        LIMIT ?
    """, (limit,))
    
    jobs = c.fetchall()
    logger.info(f"Verifying {len(jobs)} top-ranked opportunities...")
    
    def process_job(job):
        job_id, url = job
        status, http_code = verify_url(url)
        return (job_id, status, http_code)
        
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_job = {executor.submit(process_job, job): job for job in jobs}
        for future in concurrent.futures.as_completed(future_to_job):
            try:
                results.append(future.result())
            except Exception as e:
                pass
                
    # Update DB
    updated = 0
    closed = 0
    for job_id, status, http_code in results:
        c.execute("""
            UPDATE jobs 
            SET verification_status = ?, 
                http_status = ?, 
                last_verified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, http_code, job_id))
        
        if status == 'CLOSED':
            # Optionally lower the ranking score so it disappears
            c.execute("UPDATE jobs SET ranking_score = ranking_score - 1000 WHERE id = ?", (job_id,))
            closed += 1
            
        updated += 1
        
    conn.commit()
    conn.close()
    
    logger.info(f"Verification complete: {updated} checked, {closed} found closed and removed from top ranking.")

if __name__ == "__main__":
    verify_top_opportunities(limit=100)
