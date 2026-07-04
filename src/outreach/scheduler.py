import schedule
import time
from datetime import datetime
from src.outreach.run_batch import run_daily_outreach

def job():
    print(f"\n[SCHEDULER] Triggering daily outreach job at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_daily_outreach(400)
    save_scheduler_state()

import json
import os

STATE_FILE = "data/scheduler_state.json"

def get_scheduler_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_scheduler_state():
    state = {
        "last_run": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)



def start_scheduler():
    print("==================================================")
    print("⏰ OUTREACH SCHEDULER STARTED")
    print("Configured to run daily at 09:00 system time.")
    print("==================================================")

    # Check for missed execution today
    state = get_scheduler_state()
    last_run = state.get("last_run", "")
    now = datetime.now()
    today_str = now.strftime('%Y-%m-%d')
    
    # If we haven't run today, run immediately.
    if not last_run.startswith(today_str):
        print(f"⚠️ Missed schedule for today. Running recovery job now...")
        job()
    elif last_run.startswith(today_str):
        print(f"✅ Already executed today at {last_run}. Waiting for tomorrow.")

    # Schedule the job every day at 09:00
    schedule.every().day.at("09:00").do(job)

    print("Press Ctrl+C to exit.")
    while True:
        try:
            schedule.run_pending()
            time.sleep(60) # Sleep for 60 seconds
        except KeyboardInterrupt:
            print("\nScheduler manually stopped.")
            break
        except Exception as e:
            print(f"Scheduler encountered an error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    start_scheduler()
