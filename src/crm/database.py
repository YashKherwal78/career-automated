import sqlite3
import os
from datetime import datetime, date
from typing import Dict, List, Optional
from src.config.config import Config

DB_PATH = Config.DATABASE_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT UNIQUE NOT NULL,
            domain TEXT,
            hr_name TEXT,
            hr_email TEXT,
            founder_name TEXT,
            founder_role TEXT,
            founder_email TEXT,
            founder_linkedin TEXT,
            cto_name TEXT,
            cto_email TEXT,
            employee_count TEXT,
            careers_page TEXT,
            hr_contacted INTEGER DEFAULT 0,
            hr_contact_date TEXT,
            hr_replied INTEGER DEFAULT 0,
            founder_contacted INTEGER DEFAULT 0,
            founder_contact_date TEXT,
            founder_replied INTEGER DEFAULT 0,
            interview_scheduled INTEGER DEFAULT 0,
            bounced INTEGER DEFAULT 0,
            status TEXT DEFAULT 'New',
            agent_metadata TEXT,
            days_old INTEGER DEFAULT 0,
            job_match_score INTEGER DEFAULT 0,
            resume_match_score INTEGER DEFAULT 0,
            resume_family TEXT,
            generated_email_body TEXT,
            reply_body TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_daily_stats() -> Dict:
    conn = get_connection()
    cursor = conn.cursor()
    today = date.today().isoformat()
    
    # Emails sent today
    cursor.execute("SELECT COUNT(*) FROM leads WHERE hr_contact_date LIKE ? OR founder_contact_date LIKE ?", (f"{today}%", f"{today}%"))
    emails_sent = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE hr_replied = 1 OR founder_replied = 1")
    replies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE bounced = 1")
    bounces = cursor.fetchone()[0]
    
    conn.close()
    return {"emails_sent": emails_sent, "replies": replies, "bounces": bounces}

def get_all_uncontacted_scored_leads() -> List[Dict]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    # Scored leads that haven't been contacted
    cursor.execute("SELECT * FROM leads WHERE status IN ('Scored', 'Enriched', 'Resume Tailored') AND hr_contacted = 0 AND founder_contacted = 0")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_or_update_lead(company_name: str, data: Dict):
    """Upserts a lead based on company_name"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM leads WHERE company_name = ?", (company_name,))
    row = cursor.fetchone()
    
    if row:
        # Update existing
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        values = list(data.values())
        values.append(company_name)
        cursor.execute(f"UPDATE leads SET {set_clause} WHERE company_name = ?", values)
    else:
        # Insert new
        data["company_name"] = company_name
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())
        cursor.execute(f"INSERT INTO leads ({columns}) VALUES ({placeholders})", values)
        
    conn.commit()
    conn.close()

def get_lead(company_name: str) -> Optional[Dict]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE company_name = ?", (company_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_leads_by_status(status: str) -> List[Dict]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE status = ?", (status,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_status(company_name: str, new_status: str, update_date_field: str = None):
    data = {"status": new_status}
    if update_date_field:
        data[update_date_field] = datetime.now().isoformat()
        if new_status == 'HR Contacted':
            data["hr_contacted"] = 1
        elif new_status == 'Founder Contacted':
            data["founder_contacted"] = 1
        elif new_status == 'HR Replied':
            data["hr_replied"] = 1
        elif new_status == 'Founder Replied':
            data["founder_replied"] = 1
        elif new_status == 'Interview Scheduled':
            data["interview_scheduled"] = 1
            
    add_or_update_lead(company_name, data)

def get_lead_by_hr_email(email: str) -> Optional[Dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads WHERE hr_email = ? OR founder_email = ?", (email, email))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
