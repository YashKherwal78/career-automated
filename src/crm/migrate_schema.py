import sqlite3
from config import Config

def migrate_database():
    print(f"Migrating database {Config.DATABASE_PATH}...")
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()

    # 1. Create Experiments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            subject_variant TEXT,
            email_variant TEXT,
            resume_family TEXT,
            contact_type TEXT,
            reply INTEGER DEFAULT 0,
            positive_reply INTEGER DEFAULT 0,
            interview INTEGER DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    # 2. Add new columns to leads table
    new_columns = [
        ("enrichment_cost", "REAL DEFAULT 0.0"),
        ("llm_cost", "REAL DEFAULT 0.0"),
        ("total_cost", "REAL DEFAULT 0.0"),
        ("domain_confidence", "REAL DEFAULT 0.0"),
        ("contact_confidence", "REAL DEFAULT 0.0"),
        ("classification_confidence", "REAL DEFAULT 0.0"),
        ("reply_probability", "REAL DEFAULT 0.0"),
        ("interview_probability", "REAL DEFAULT 0.0"),
        ("last_enriched_date", "TEXT"),
        ("enrichment_source", "TEXT"),
        ("resume_family", "TEXT"),
        ("hiring_manager_name", "TEXT"),
        ("hiring_manager_email", "TEXT")
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
