from src.api.db import get_connection
from src.system.logger import setup_logger
logger = setup_logger('app_queue')
import sqlite3
import datetime
from src.config.config import Config

def generate_daily_queue():
    """
    Generates the daily application queue by isolating the top 20 HIGH priority jobs.
    """
    logger.info("Agent 0: Generating Daily Application Queue...")
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Check how many jobs are already queued today
    cursor.execute("SELECT COUNT(*) FROM application_queue WHERE queue_date = ?", (today,))
    queued_today = cursor.fetchone()[0]
    
    remaining_slots = 20 - queued_today
    
    if remaining_slots <= 0:
        logger.info(f"Queue is already full for today ({queued_today}/20).")
        conn.close()
        return

    # Fetch top eligible jobs not already queued today
    query = """
        SELECT * FROM jobs 
        WHERE eligibility_status = 'Eligible' 
        AND judge_decision IN ('STRONG_APPLY', 'APPLY', 'MAYBE')
        AND id NOT IN (SELECT job_id FROM application_queue WHERE queue_date = ?)
        ORDER BY 
            CASE judge_decision 
                WHEN 'STRONG_APPLY' THEN 1 
                WHEN 'APPLY' THEN 2 
                WHEN 'MAYBE' THEN 3 
                ELSE 4 
            END ASC,
            ranking_score DESC 
        LIMIT 100
    """
    
    cursor.execute(query, (today,))
    top_jobs = cursor.fetchall()
    
    queued = 0
    company_counts = {}
    
    for job in top_jobs:
        company = job["company_name"]
        
        # Max 2 jobs per company limit
        if company_counts.get(company, 0) >= 2:
            continue
            
        cursor.execute('''
            INSERT INTO application_queue (
                job_id, company, title, ats_url, ranking_score, 
                eligibility_score, recommended_resume, resume_confidence, 
                queue_date, queue_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job["id"],
            company,
            job["job_title"],
            job["job_url"],
            job["ranking_score"],
            job["eligibility_score"],
            job["recommended_resume"],
            job["resume_confidence"],
            today,
            'QUEUED'
        ))
        
        company_counts[company] = company_counts.get(company, 0) + 1
        queued += 1
        
        if queued >= remaining_slots:
            break
        
    conn.commit()
    conn.close()
    
    logger.info(f"Queue generation complete. Added {queued} jobs to today's queue.")

if __name__ == "__main__":
    generate_daily_queue()
