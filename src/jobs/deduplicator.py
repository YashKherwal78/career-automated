import re
import sqlite3
import json
from typing import Dict, Optional
from src.config.config import Config

def generate_canonical_id(company: str, title: str, location: str, job_url: str) -> str:
    """
    Generates a canonical ID for a job.
    Prefers ATS Job ID from the URL if extractable (Greenhouse, Lever, Ashby).
    Falls back to slugified company+title+location.
    """
    # Try to extract ATS ID
    if "greenhouse.io" in job_url or "lever.co" in job_url or "ashbyhq.com" in job_url:
        # Simple extraction: last part of URL path is usually the ID
        parts = [p for p in job_url.split('/') if p.strip()]
        if parts:
            ats_id = parts[-1].split('?')[0] # remove query params
            return f"ats_{ats_id.lower()}"
            
    # Fallback to slug
    raw = f"{company}-{title}-{location}".lower()
    slug = re.sub(r'[^a-z0-9]+', '-', raw).strip('-')
    return slug

def is_ats_url(url: str) -> bool:
    return any(ats in url for ats in ["greenhouse.io", "lever.co", "ashbyhq.com", "workday", "myworkdayjobs"])

def process_job(job: Dict) -> None:
    """
    Adds a job to the database or updates it if it's a duplicate.
    Prioritizes ATS URLs.
    """
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    company = job.get("company_name", "")
    title = job.get("job_title", "")
    location = job.get("location", "")
    url = job.get("job_url", "")
    source = job.get("source", "Unknown")
    
    canonical_id = generate_canonical_id(company, title, location, url)
    
    # Check if exists
    cursor.execute("SELECT * FROM jobs WHERE canonical_id = ?", (canonical_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Duplicate found
        new_duplicate_count = existing["duplicate_count"] + 1
        
        # Merge sources
        sources = []
        if existing["sources_found_in"]:
            try:
                sources = json.loads(existing["sources_found_in"])
            except:
                sources = [existing["sources_found_in"]]
        if source not in sources:
            sources.append(source)
            
        # Determine URL priority
        final_url = existing["job_url"]
        if is_ats_url(url) and not is_ats_url(existing["job_url"]):
            final_url = url # Override with ATS URL
            
        cursor.execute('''
            UPDATE jobs SET 
                duplicate_count = ?,
                sources_found_in = ?,
                job_url = ?
            WHERE id = ?
        ''', (new_duplicate_count, json.dumps(sources), final_url, existing["id"]))
        
    else:
        # New job
        cursor.execute("""
            INSERT INTO jobs (
                company_name, job_title, job_url, job_description, location, 
                experience_required, skills_required, employment_type, posting_date, 
                days_old, canonical_id, duplicate_count, sources_found_in, source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company,
            title,
            url,
            job.get("job_description", ""),
            location,
            job.get("experience_required", ""),
            job.get("skills_required", ""),
            job.get("employment_type", ""),
            job.get("posting_date", ""),
            job.get("days_old", 0),
            canonical_id,
            0,
            json.dumps([source]),
            source
        ))
        
        # Also create a linked Lead record so the pipeline can process it
        job_id = cursor.lastrowid
        cursor.execute("""
            INSERT OR IGNORE INTO leads (company_name, job_id, job_title, job_url, status)
            VALUES (?, ?, ?, ?, 'New')
        """, (company, job_id, title, url))
        
    conn.commit()
    conn.close()
