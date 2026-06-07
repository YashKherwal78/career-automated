import sqlite3
from src.config.config import Config
from src.jobs.providers.csv_provider import CSVProvider
from src.jobs.providers.apify_provider import ApifyProvider

def ingest_jobs(provider_type="apify"):
    """Agent 0: Discovers jobs from the selected provider and loads them into the database."""
    print(f"Agent 0: Ingesting jobs from {provider_type} provider...")
    
    if provider_type == "csv":
        provider = CSVProvider(str(Config.DATA_DIR / "jobs.csv"))
    elif provider_type == "apify":
        provider = ApifyProvider()
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
        
    jobs = provider.discover_jobs()
    
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    jobs_ingested = 0
    for job in jobs:
        # Check if job already exists based on URL
        cursor.execute("SELECT id FROM jobs WHERE job_url = ?", (job["job_url"],))
        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO jobs (company_name, job_title, job_url, job_description, location, experience_required, skills_required, employment_type, posting_date, days_old)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("company_name", ""),
                job.get("job_title", ""),
                job.get("job_url", ""),
                job.get("job_description", ""),
                job.get("location", ""),
                job.get("experience_required", ""),
                job.get("skills_required", ""),
                job.get("employment_type", ""),
                job.get("posting_date", ""),
                job.get("days_old", 0)
            ))
            
            # Also create a linked Lead record so the pipeline can process it
            job_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO leads (company_name, job_id, job_title, job_url, status)
                VALUES (?, ?, ?, ?, 'New')
            """, (job.get("company_name", ""), job_id, job.get("job_title", ""), job.get("job_url", "")))
            
            jobs_ingested += 1
            
    conn.commit()
    conn.close()
    print(f"Agent 0: Successfully ingested {jobs_ingested} new jobs from {provider_type}.")

if __name__ == "__main__":
    # Apify is the production default
    ingest_jobs(provider_type="apify")
