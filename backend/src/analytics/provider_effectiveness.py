from src.system.logger import setup_logger
logger = setup_logger('provider_effectiveness')
import sqlite3
from src.config.config import Config

DB_PATH = Config.DATABASE_PATH

def init_analytics_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS provider_analytics (
            provider_name TEXT PRIMARY KEY,
            companies_scanned INTEGER DEFAULT 0,
            jobs_found INTEGER DEFAULT 0,
            opportunities_displayed INTEGER DEFAULT 0,
            applications_submitted INTEGER DEFAULT 0,
            recruiter_replies INTEGER DEFAULT 0,
            interviews INTEGER DEFAULT 0,
            offers INTEGER DEFAULT 0,
            scan_priority INTEGER DEFAULT 50,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def record_discovery_run(provider_name: str, companies_scanned: int, jobs_found: int, opportunities_displayed: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO provider_analytics (provider_name, companies_scanned, jobs_found, opportunities_displayed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(provider_name) DO UPDATE SET
            companies_scanned = companies_scanned + excluded.companies_scanned,
            jobs_found = jobs_found + excluded.jobs_found,
            opportunities_displayed = opportunities_displayed + excluded.opportunities_displayed,
            last_updated = CURRENT_TIMESTAMP
    """, (provider_name, companies_scanned, jobs_found, opportunities_displayed))
    conn.commit()
    conn.close()

def record_application_outcome(provider_name: str, metric: str, count: int = 1):
    valid_metrics = ["applications_submitted", "recruiter_replies", "interviews", "offers"]
    if metric not in valid_metrics:
        raise ValueError(f"Invalid metric. Must be one of {valid_metrics}")
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # We must ensure the provider exists first
    c.execute("INSERT OR IGNORE INTO provider_analytics (provider_name) VALUES (?)", (provider_name,))
    
    c.execute(f"""
        UPDATE provider_analytics
        SET {metric} = {metric} + ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE provider_name = ?
    """, (count, provider_name))
    
    conn.commit()
    conn.close()
    
    # Recalculate priority after outcome
    adjust_provider_priority(provider_name)

def adjust_provider_priority(provider_name: str):
    """
    Historical outcomes automatically adjust provider scan priority.
    Providers producing interviews receive higher scan frequency.
    Providers producing consistently poor opportunities receive lower scan frequency.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT applications_submitted, interviews, jobs_found FROM provider_analytics WHERE provider_name = ?", (provider_name,))
    row = c.fetchone()
    if not row:
        return
        
    apps, interviews, jobs = row
    
    new_priority = 50 # Default baseline
    
    # Positive signals
    if interviews > 0:
        new_priority += (interviews * 20) # Massive boost for actual interviews
    elif apps > 0:
        new_priority += (apps * 2) # Small boost for viable applications
        
    # Negative signals (high volume, low signal)
    if jobs > 500 and apps == 0:
        new_priority -= 30 # Penalty for noise
        
    # Cap between 1 and 100
    new_priority = max(1, min(100, new_priority))
    
    c.execute("UPDATE provider_analytics SET scan_priority = ? WHERE provider_name = ?", (new_priority, provider_name))
    conn.commit()
    conn.close()

def generate_effectiveness_report():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM provider_analytics ORDER BY scan_priority DESC, interviews DESC")
    rows = c.fetchall()
    
    logger.info(f"{'Provider':<20} | {'Scanned':<8} | {'Jobs':<6} | {'Apps':<6} | {'Intervs':<7} | {'Success%':<8} | {'Priority':<8}")
    logger.info("-" * 80)
    for row in rows:
        provider = row[0]
        scanned = row[1]
        jobs = row[2]
        apps = row[4]
        interviews = row[6]
        priority = row[8]
        
        success_pct = 0
        if apps > 0:
            success_pct = (interviews / apps) * 100
            
        logger.info(f"{provider:<20} | {scanned:<8} | {jobs:<6} | {apps:<6} | {interviews:<7} | {success_pct:>.1f}%    | {priority:<8}")
        
    conn.close()

if __name__ == "__main__":
    init_analytics_schema()
    logger.info("Analytics schema initialized.")
    # generate_effectiveness_report()
