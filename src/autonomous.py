import time
import schedule
from datetime import datetime
from src.jobs.discovery import ingest_jobs
from src.orchestrator import run_batch_operations
from src.outreach.inbox_reader import monitor_inbox
from src.outreach.briefing import generate_and_send_briefing

def run_discovery_phase():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 STARTING DISCOVERY PHASE")
    try:
        # Use apify (but fallback to csv in the script if needed)
        ingest_jobs("apify")
    except Exception as e:
        print(f"Discovery phase failed: {e}")

def run_outreach_phase():
    now = datetime.now()
    if 9 <= now.hour < 21:
        print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🚀 STARTING OUTREACH PHASE")
        try:
            # We'll rely on orchestrator's run_batch_operations to pick up new leads
            # It already restricts to max_daily_emails
            run_batch_operations()
        except Exception as e:
            print(f"Outreach phase failed: {e}")
    else:
        print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Outside outreach window (09:00 - 21:00). Skipping.")

def run_inbox_monitor():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📥 CHECKING INBOX")
    try:
        monitor_inbox()
    except Exception as e:
        print(f"Inbox monitor failed: {e}")

def run_briefing():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 GENERATING DAILY BRIEFING")
    try:
        generate_and_send_briefing()
    except Exception as e:
        print(f"Briefing failed: {e}")

if __name__ == "__main__":
    print("=======================================================")
    print("🤖 AUTONOMOUS RECRUITING PLATFORM V1 INITIATED")
    print("=======================================================")
    
    # Schedule
    schedule.every().day.at("07:00").do(run_discovery_phase)
    schedule.every(30).minutes.do(run_outreach_phase)
    schedule.every().hour.do(run_inbox_monitor)
    schedule.every().day.at("22:00").do(run_briefing)
    
    print("Schedule Loaded:")
    for job in schedule.jobs:
        print(f" - {job}")
        
    print("\nSystem running. Press Ctrl+C to stop.")
    
    # Run inbox monitor immediately on startup just to test
    run_inbox_monitor()
    
    while True:
        schedule.run_pending()
        time.sleep(60)
