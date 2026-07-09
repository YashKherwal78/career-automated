from src.system.logger import setup_logger
logger = setup_logger('run_batch')
import os
import sqlite3
from datetime import datetime
from src.outreach.engine import OutreachEngine
from src.crm.database import get_connection
from src.config.config import Config

def check_duplicate_run(limit: int) -> bool:
    """
    Checks if we have already sent the daily limit of emails today.
    Returns True if we hit the limit, False otherwise.
    """
    conn = get_connection()
    c = conn.cursor()
    # Count how many emails have status = 'sent' today
    # Note: sqlite date('now') uses UTC, so we should be careful. 
    # Using python's local date for consistency.
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    c.execute("""
        SELECT COUNT(*) FROM outreach_log 
        WHERE status = 'SENT' 
        AND date(sent_timestamp, 'localtime') = ?
    """, (today_str,))
    
    sent_today = c.fetchone()[0]
    conn.close()
    
    logger.info(f"[Duplicate Protection] Emails already sent today ({today_str} local): {sent_today}/{limit}")
    return sent_today >= limit

def run_daily_outreach(target_limit: int = 400):
    logger.info("==================================================")
    logger.info(f"🚀 STARTING DAILY OUTREACH BATCH (Target: {target_limit})")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("==================================================")

    if check_duplicate_run(target_limit):
        logger.info("\n[ABORT] Daily limit already reached. Duplicate run prevented.")
        return

    # Initialize Engine
    engine = OutreachEngine(dry_run=False)
    engine.limit = target_limit
    
    files_to_process = [
        "data/clean_leads.xlsx", 
        "data/leads_cleaned.xlsx", 
        "data/leads.xlsx", 
        "data/Gend phad HR data.xlsx"
    ]
    
    for file_path in files_to_process:
        if os.path.exists(file_path):
            # Check mid-run if we hit the limit across files
            if check_duplicate_run(target_limit):
                logger.info(f"\nTarget limit of {target_limit} reached mid-batch. Stopping.")
                break
                
            logger.info(f"\n--- PROCESSING FILE: {file_path} ---")
            # Monkey patch the file getter so the engine processes this specific file
            engine.get_latest_excel = lambda f=file_path: f
            
            try:
                engine.run_daily_batch()
            except Exception as e:
                logger.info(f"Error processing {file_path}: {e}")
                
        else:
            logger.info(f"\n--- SKIPPING: {file_path} (File not found) ---")

    logger.info("\n==================================================")
    logger.info("🏁 DAILY OUTREACH BATCH COMPLETE")
    logger.info("==================================================")

if __name__ == "__main__":
    run_daily_outreach(400)
