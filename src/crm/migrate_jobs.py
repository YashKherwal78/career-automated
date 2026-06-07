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
            status TEXT DEFAULT 'New'
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
        ("agent_metadata", "TEXT")
    ]

    for col_name, col_type in new_columns:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == "__main__":
    migrate_database()
