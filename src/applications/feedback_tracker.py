import sqlite3
import os
import json
from src.config.config import Config

class FeedbackTracker:
    def __init__(self):
        self.db_path = os.path.join(Config.DATA_DIR, "crm.db")
        self._init_db()
        
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS application_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            role TEXT,
            opportunity_score INTEGER,
            why_this_job TEXT,
            resume_version TEXT,
            project_ordering TEXT,
            application_answers TEXT,
            outcome TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        conn.close()
        
    def log_outcome(self, company: str, role: str, score: int, why: str, resume_ver: str, projects: list, answers: dict, outcome: str):
        """
        outcome should be 'INTERVIEW' or 'REJECTED'
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        INSERT INTO application_outcomes 
        (company, role, opportunity_score, why_this_job, resume_version, project_ordering, application_answers, outcome)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company, 
            role, 
            score, 
            why, 
            resume_ver, 
            json.dumps(projects), 
            json.dumps(answers), 
            outcome
        ))
        conn.commit()
        conn.close()
        print(f"[FeedbackTracker] Logged {outcome} for {role} at {company}")

if __name__ == "__main__":
    # Seed mock data for V1.3 report generation
    tracker = FeedbackTracker()
    tracker.log_outcome("Acme AI", "Founder's Office", 88, "Early stage startup", "Master Resume", ["CareerAutomated", "YAAR"], {}, "INTERVIEW")
    tracker.log_outcome("Groww", "Associate Product Manager", 85, "Technical role", "Master Resume", ["YAAR"], {}, "REJECTED")
    tracker.log_outcome("PhonePe", "Site Reliability Engineer", 60, "Low Experience", "Master Resume", ["RAG"], {}, "REJECTED")
    tracker.log_outcome("OpenAI", "AI Product Manager", 95, "GenAI Domain", "Agent 5", ["CareerAutomated", "Orange Labs"], {}, "INTERVIEW")
    tracker.log_outcome("Stripe", "Product Analyst", 80, "Fintech", "Master Resume", ["ScoreMe"], {}, "INTERVIEW")
    tracker.log_outcome("BigCorp", "Associate Product Manager", 78, "Large org", "Master Resume", ["YAAR"], {}, "REJECTED")
