import sqlite3
from src.config.config import Config

def migrate_database():
    print(f"Migrating database {Config.DATABASE_PATH}...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()

    # Create Jobs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            job_title TEXT,
            job_url TEXT,
            job_description TEXT,
            location TEXT,
            experience_required TEXT,
            skills_required TEXT,
            employment_type TEXT,
            posting_date TEXT,
            days_old INTEGER DEFAULT 0,
            status TEXT DEFAULT 'New',
            canonical_id TEXT UNIQUE,
            duplicate_count INTEGER DEFAULT 0,
            sources_found_in TEXT,
            quality_score INTEGER DEFAULT 0,
            quality_reason TEXT,
            source TEXT,
            eligibility_score INTEGER DEFAULT 0,
            eligibility_status TEXT DEFAULT 'Pending',
            boosts TEXT,
            penalties TEXT,
            application_priority TEXT,
            rejection_reason TEXT,
            ranking_score INTEGER DEFAULT 0,
            ranking_reason TEXT,
            recommended_resume TEXT,
            resume_confidence INTEGER DEFAULT 0
        )
    ''')
    
    # Create Application Queue Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            company TEXT,
            title TEXT,
            ats_url TEXT,
            ranking_score INTEGER,
            eligibility_score INTEGER,
            recommended_resume TEXT,
            resume_confidence INTEGER,
            queue_date TEXT,
            queue_status TEXT DEFAULT 'QUEUED',
            application_notes TEXT,
            UNIQUE(job_id, queue_date)
        )
    ''')
    
    # Create Contacts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            name TEXT,
            title TEXT,
            linkedin_url TEXT,
            confidence_score REAL,
            source TEXT DEFAULT 'APIFY',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Apify Metrics Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apify_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            endpoint TEXT,
            calls_made INTEGER DEFAULT 0,
            credits_consumed REAL DEFAULT 0.0,
            cost_usd REAL DEFAULT 0.0,
            contacts_found INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Add new columns to leads table
    new_columns = [
        ("job_id", "INTEGER"),
        ("job_title", "TEXT"),
        ("job_url", "TEXT"),
        ("job_match_score", "INTEGER DEFAULT 0"),
        ("resume_match_score", "INTEGER DEFAULT 0"),
        ("skill_gap_analysis", "TEXT"),
        ("selected_resume", "TEXT"),
        ("selected_project", "TEXT"),
        ("days_old", "INTEGER DEFAULT 0"),
    ]

    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to leads")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                print(f"Error adding {col_name} to leads: {e}")
                
    jobs_new_columns = [
        ("canonical_id", "TEXT UNIQUE"),
        ("duplicate_count", "INTEGER DEFAULT 0"),
        ("sources_found_in", "TEXT"),
        ("eligibility_score", "INTEGER DEFAULT 0"),
        ("eligibility_status", "TEXT DEFAULT 'Pending'"),
        ("boosts", "TEXT"),
        ("penalties", "TEXT"),
        ("application_priority", "TEXT"),
        ("rejection_reason", "TEXT"),
        ("ranking_score", "INTEGER DEFAULT 0"),
        ("ranking_reason", "TEXT"),
        ("recommended_resume", "TEXT"),
        ("resume_confidence", "INTEGER DEFAULT 0")
    ]
    
    for col_name, col_type in jobs_new_columns:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name} to jobs")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                print(f"Error adding {col_name} to jobs: {e}")

    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == "__main__":
    migrate_database()
