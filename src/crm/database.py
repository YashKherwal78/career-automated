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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referral_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            job_title TEXT,
            contact_name TEXT NOT NULL,
            linkedin_url TEXT UNIQUE,
            email TEXT,
            email_confidence INTEGER DEFAULT 0,
            contact_type TEXT,
            discovery_source TEXT,
            profile_confidence INTEGER DEFAULT 0,
            raw_profile_json TEXT,
            referral_score INTEGER DEFAULT 0,
            ranking_reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS application_answer_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            company TEXT,
            role TEXT,
            question_text TEXT,
            field_label TEXT,
            field_type TEXT,
            placeholder TEXT,
            options TEXT,
            question_category TEXT,
            raw_answer TEXT,
            normalized_answer TEXT,
            answer_source TEXT,
            confidence INTEGER,
            css_selector TEXT,
            input_tag TEXT,
            required BOOLEAN,
            visible BOOLEAN,
            disabled BOOLEAN,
            validation_error TEXT,
            current_value TEXT,
            final_value TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS outreach_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            recruiter_name TEXT,
            company TEXT,
            role TEXT,
            subject TEXT,
            body TEXT,
            sent_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacted_emails (
            email TEXT PRIMARY KEY,
            first_contact_date TEXT,
            last_contact_date TEXT,
            contact_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_intelligence_cache (
            company_name TEXT PRIMARY KEY,
            domain TEXT,
            employee_count TEXT,
            is_hiring INTEGER,
            priority_score INTEGER,
            last_updated TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS llm_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workload TEXT,
            provider TEXT,
            model TEXT,
            tokens INTEGER,
            latency REAL,
            fallback_count INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discovered_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            description TEXT,
            employee_count TEXT,
            source TEXT,
            status TEXT DEFAULT 'DISCOVERED',
            opportunity_score INTEGER DEFAULT 0,
            why_this_job TEXT,
            rejection_reason TEXT,
            outreach_scheduled_for DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS worker_heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at DATETIME,
            finished_at DATETIME,
            execution_time REAL,
            items_processed INTEGER,
            last_error TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT,
            greenhouse_slug TEXT UNIQUE,
            historical_opportunities_found INTEGER DEFAULT 0,
            interviews_generated INTEGER DEFAULT 0,
            replies_generated INTEGER DEFAULT 0,
            last_relevant_opportunity DATETIME,
            confidence_score INTEGER DEFAULT 50,
            status TEXT DEFAULT 'ACTIVE',
            ats_provider TEXT,
            website TEXT,
            discovery_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_board_sync DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_intelligence_static (
            company_name TEXT PRIMARY KEY,
            website TEXT,
            ats_provider TEXT,
            greenhouse_slug TEXT,
            lever_slug TEXT,
            ashby_slug TEXT,
            yc_batch TEXT,
            funding_stage TEXT,
            investors TEXT,
            headquarters TEXT,
            industry TEXT,
            hiring_in_india BOOLEAN DEFAULT 0,
            careers_url TEXT,
            hiring_countries TEXT,
            last_scan DATETIME,
            last_job_count INTEGER DEFAULT 0,
            career_page_health TEXT,
            discovery_source TEXT,
            ai_relevance INTEGER DEFAULT 0,
            pm_relevance INTEGER DEFAULT 0,
            outreach_priority TEXT DEFAULT 'LOW',
            application_priority TEXT DEFAULT 'LOW',
            scan_priority_score INTEGER DEFAULT 0,
            lifecycle_status TEXT DEFAULT 'DISCOVERED',
            remote_hiring BOOLEAN DEFAULT 0,
            founder_office_probability REAL DEFAULT 0.0,
            scan_frequency TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hiring_intelligence_dynamic (
            company_name TEXT PRIMARY KEY,
            last_job_seen DATETIME,
            last_successful_sync DATETIME,
            last_checked DATETIME,
            last_error TEXT,
            active_job_count INTEGER DEFAULT 0,
            pm_job_count INTEGER DEFAULT 0,
            apm_job_count INTEGER DEFAULT 0,
            ai_job_count INTEGER DEFAULT 0,
            founder_office_job_count INTEGER DEFAULT 0,
            hiring_velocity REAL DEFAULT 0.0,
            hiring_frequency TEXT,
            confidence_score REAL DEFAULT 1.0,
            consecutive_failures INTEGER DEFAULT 0,
            FOREIGN KEY (company_name) REFERENCES company_intelligence_static (company_name)
        )
        ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS final_company_registry (
            company_name TEXT PRIMARY KEY,
            ats_provider TEXT,
            ats_slug TEXT,
            ats_base_url TEXT,
            ats_detection_method TEXT,
            ats_last_verified DATETIME,
            priority TEXT DEFAULT 'P2',
            discovery_source TEXT,
            connector_status TEXT DEFAULT 'UNKNOWN',
            connector_error TEXT,
            last_scan DATETIME,
            last_successful_scan DATETIME,
            times_scanned INTEGER DEFAULT 0,
            active_jobs INTEGER DEFAULT 0,
            scan_frequency TEXT DEFAULT 'Daily',
            workday_tenant TEXT,
            workday_region TEXT,
            workday_version TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS discovery_strategy (
            strategy_id TEXT PRIMARY KEY,
            provider TEXT,
            backend TEXT,
            ats TEXT,
            query TEXT,
            location TEXT,
            startup_filter TEXT,
            rule_version TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1,
            executions INTEGER DEFAULT 0,
            opportunities_discovered INTEGER DEFAULT 0,
            unique_companies INTEGER DEFAULT 0,
            eligible_opportunities INTEGER DEFAULT 0,
            duplicate_rate REAL DEFAULT 0.0,
            average_latency REAL DEFAULT 0.0,
            average_cost REAL DEFAULT 0.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_discovery_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            source TEXT NOT NULL,
            discovery_type TEXT,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            confidence INTEGER DEFAULT 1,
            reliability_score REAL DEFAULT 0.5,
            UNIQUE(company_name, source, discovery_type)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ats_learning_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            ats_provider TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            successful_extractions INTEGER DEFAULT 0,
            failed_extractions INTEGER DEFAULT 0,
            first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed_at DATETIME,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS data_source_sync_state (
            source_id TEXT PRIMARY KEY,
            source_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            last_sync DATETIME DEFAULT CURRENT_TIMESTAMP,
            sync_token TEXT,
            status TEXT,
            metadata TEXT,
            last_success DATETIME,
            consecutive_failures INTEGER DEFAULT 0,
            average_sync_duration REAL DEFAULT 0.0,
            last_error TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS opportunity_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            location TEXT,
            remote BOOLEAN,
            experience TEXT,
            source TEXT,
            ats TEXT,
            url TEXT UNIQUE NOT NULL,
            strategy_id TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            eligibility_status TEXT,
            eligibility_decision TEXT,
            rule_version TEXT,
            matched_rule TEXT,
            raw_payload TEXT,
            status TEXT DEFAULT 'NEW',
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_all_contacted_emails() -> set:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM contacted_emails")
    rows = cursor.fetchall()
    conn.close()
    return {r[0] for r in rows}

def upsert_contacted_email(email: str, contact_date: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacted_emails WHERE email = ?", (email,))
    row = cursor.fetchone()
    if row:
        # Check if this date is earlier than first or later than last
        first_date = min(row[1], contact_date) if row[1] else contact_date
        last_date = max(row[2], contact_date) if row[2] else contact_date
        count = row[3] + 1
        cursor.execute("UPDATE contacted_emails SET first_contact_date = ?, last_contact_date = ?, contact_count = ? WHERE email = ?", 
                       (first_date, last_date, count, email))
    else:
        cursor.execute("INSERT INTO contacted_emails (email, first_contact_date, last_contact_date, contact_count) VALUES (?, ?, ?, 1)",
                       (email, contact_date, contact_date))
    conn.commit()
    conn.close()

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

def get_cached_intelligence(company_name: str) -> Optional[Dict]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM company_intelligence_cache WHERE company_name = ?", (company_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d['is_hiring'] = bool(d['is_hiring'])
        return d
    return None

def set_cached_intelligence(company_name: str, intel: Dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO company_intelligence_cache 
        (company_name, domain, employee_count, is_hiring, priority_score, last_updated)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (
        company_name, 
        intel.get('domain', ''),
        str(intel.get('employee_count', '')),
        1 if intel.get('is_hiring') else 0,
        intel.get('priority_score', 0)
    ))
    conn.commit()
    conn.close()

def log_llm_usage(workload: str, provider: str, model: str, tokens: int, latency: float, fallback_count: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO llm_usage_log (workload, provider, model, tokens, latency, fallback_count)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (workload, provider, model, tokens, latency, fallback_count))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")

def insert_discovered_job(data: Dict) -> bool:
    """Inserts a job if URL is unique. Returns True if inserted, False if duplicate."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        cursor.execute(f"INSERT INTO discovered_jobs ({columns}) VALUES ({placeholders})", list(data.values()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_jobs_by_status(status: str, limit: int = None) -> List[Dict]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT * FROM discovered_jobs WHERE status = ?"
    if limit:
        query += f" LIMIT {limit}"
    cursor.execute(query, (status,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_job_status(job_id: int, new_status: str, extra_data: Dict = None):
    conn = get_connection()
    cursor = conn.cursor()
    query = "UPDATE discovered_jobs SET status = ?, updated_at = CURRENT_TIMESTAMP"
    values = [new_status]
    if extra_data:
        for k, v in extra_data.items():
            query += f", {k} = ?"
            values.append(v)
    query += " WHERE id = ?"
    values.append(job_id)
    cursor.execute(query, values)
    conn.commit()
    conn.close()

def log_heartbeat(worker_name: str, status: str, started_at: str, finished_at: str, execution_time: float, items: int, error: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO worker_heartbeats (worker_name, status, started_at, finished_at, execution_time, items_processed, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (worker_name, status, started_at, finished_at, execution_time, items, error))
        conn.commit()
    except Exception as e:
        print(f"Error logging heartbeat: {e}")
    finally:
        conn.close()

def add_to_company_registry(slug: str, company_name: str = None, ats_provider: str = 'greenhouse', website: str = None) -> bool:
    """Safely adds a verified slug to the registry, ignoring if it exists."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO company_registry (greenhouse_slug, company_name, ats_provider, website, discovery_date)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (slug, company_name or slug, ats_provider, website))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def get_active_greenhouse_slugs() -> list:
    """Returns a list of verified active greenhouse slugs with acceptable confidence."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT greenhouse_slug FROM company_registry 
        WHERE status = 'ACTIVE' AND confidence_score > 0
    ''')
    slugs = [row[0] for row in cursor.fetchall()]
    conn.close()
    return slugs

def add_to_opportunity_cache(opp: dict, decision: dict = None, strategy_id: str = None) -> bool:
    import json
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO opportunity_cache 
            (company, title, location, remote, experience, source, ats, url, strategy_id,
             eligibility_status, eligibility_decision, rule_version, matched_rule, raw_payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            opp.get("company", ""),
            opp.get("title", ""),
            opp.get("location", ""),
            opp.get("remote", False),
            opp.get("experience", ""),
            opp.get("source", ""),
            opp.get("ats", ""),
            opp.get("url", ""),
            strategy_id,
            "ELIGIBLE" if decision and decision.get("eligible") else "REJECTED" if decision else "UNKNOWN",
            json.dumps(decision) if decision else None,
            decision.get("rule_version") if decision else None,
            decision.get("matched_rule") if decision else None,
            json.dumps(opp)
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error inserting into opportunity_cache: {e}")
        return False
    finally:
        conn.close()

def add_discovery_source(company_name: str, source: str, discovery_type: str = "Company Discovery") -> int:
    """
    Upserts a discovery source for a company. Returns the total unique sources found to be used as a confidence score.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO company_discovery_sources (company_name, source, discovery_type) 
            VALUES (?, ?, ?)
            ON CONFLICT(company_name, source, discovery_type) DO UPDATE SET 
            last_seen = CURRENT_TIMESTAMP,
            confidence = confidence + 1
        ''', (company_name, source, discovery_type))
        
        cursor.execute('''
            SELECT COUNT(DISTINCT source) FROM company_discovery_sources WHERE company_name = ?
        ''', (company_name,))
        unique_sources = cursor.fetchone()[0]
        
        conn.commit()
        return unique_sources
    except Exception as e:
        print(f"Error updating discovery source: {e}")
        return 1
    finally:
        conn.close()
