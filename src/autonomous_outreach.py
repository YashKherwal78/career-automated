from src.system.logger import setup_logger
logger = setup_logger('autonomous_outreach')
import time
import schedule
from datetime import datetime
from src.jobs.discovery import ingest_jobs
from src.orchestrator import run_batch_operations
from src.outreach.inbox_reader import monitor_inbox
from src.outreach.briefing import generate_and_send_briefing

def run_discovery_phase():
    logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 STARTING DISCOVERY PHASE")
    try:
        # 1. Discover New Jobs (Safe Architecture)
        ingest_jobs("safe")
    except Exception as e:
        logger.info(f"Discovery phase failed: {e}")

def run_outreach_phase():
    now = datetime.now()
    if 9 <= now.hour < 21:
        logger.info(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 STARTING OUTREACH PHASE")
        try:
            # We'll rely on orchestrator's run_batch_operations to pick up new leads
            # It already restricts to max_daily_emails
            run_batch_operations()
        except Exception as e:
            logger.info(f"Outreach phase failed: {e}")
    else:
        logger.info(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Outside outreach window (09:00 - 21:00). Skipping.")

def run_inbox_monitor():
    logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📥 CHECKING INBOX")
    try:
        monitor_inbox()
    except Exception as e:
        logger.info(f"Inbox monitor failed: {e}")

def run_briefing():
    logger.info(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 GENERATING DAILY BRIEFING")
    try:
        generate_and_send_briefing()
    except Exception as e:
        logger.info(f"Briefing failed: {e}")

if __name__ == "__main__":
    logger.info("=======================================================")
    logger.info("🤖 AUTONOMOUS OUTREACH ENGINE V1 INITIATED")
    logger.info("=======================================================")
    
    # Schedule
    schedule.every().day.at("07:00").do(run_discovery_phase)
    schedule.every().day.at("09:00").do(run_outreach_phase)
    schedule.every().hour.do(run_inbox_monitor)
    schedule.every().day.at("22:00").do(run_briefing)
    
    logger.info("Schedule Loaded:")
    for job in schedule.jobs:
        logger.info(f" - {job}")
        
    logger.info("\nSystem running in Outreach-Only mode. Press Ctrl+C to stop.")
    
    # Run inbox monitor immediately on startup just to test
    run_inbox_monitor()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
