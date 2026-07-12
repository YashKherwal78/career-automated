import sqlite3
import json
from src.config.config import Config
from src.applications.executor import ApplicationExecutor

conn = sqlite3.connect(Config.DATABASE_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT id, company_name as company, job_title as title, location, job_url as ats_url 
    FROM jobs 
    WHERE job_url LIKE '%greenhouse%' 
    AND eligibility_status = 'Eligible' 
    ORDER BY ranking_score DESC 
    LIMIT 1 OFFSET 3
""")
jobs = cursor.fetchall()

if not jobs:
    print("No eligible Greenhouse jobs found in crm.db to test.")
    exit()

print(f"Loaded {len(jobs)} Greenhouse jobs for validation.\n")

attempted = 0
submitted = 0
paused = 0
failures = []

for job in jobs:
    attempted += 1
    resume_path = str(Config.DATA_DIR / "Resume_aiml.pdf")
    
    print(f"--- Executing Job {job['id']}: {job['title']} at {job['company']} ---")
    executor = ApplicationExecutor(
        job_id=job['id'],
        url=job['ats_url'],
        resume_path=resume_path,
        job_title=job['title'],
        company_name=job['company'],
        location=job['location']
    )
    
    import time
    start_time = time.time()
    result = executor.execute()
    elapsed = time.time() - start_time
    
    print(f"Result: {result} (in {elapsed:.1f}s)\n")
    
    if result == "SUBMITTED":
        submitted += 1
    elif result == "REVIEW_REQUIRED":
        paused += 1
        failures.append(f"{job['company']} - Human Review Required")
    else:
        failures.append(f"{job['company']} - Failed")
        
success_rate = (submitted / attempted) * 100 if attempted > 0 else 0

print("========================================")
print(" GREENHOUSE VALIDATION REPORT ")
print("========================================")
print(f"Applications Attempted: {attempted}")
print(f"Applications Submitted: {submitted}")
print(f"Applications Paused:    {paused}")
print(f"Success Rate:           {success_rate:.1f}%")
print("Failure Categories:")
for f in failures:
    print(f"  - {f}")
print("========================================")
