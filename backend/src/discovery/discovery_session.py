import yaml
import sqlite3
import uuid
import datetime
from typing import Dict, Any, List
from src.config.config import Config

class DiscoverySession:
    def __init__(self, db_path: str = Config.DATABASE_PATH):
        self.session_id = str(uuid.uuid4())
        self.started_at = datetime.datetime.now()
        self.db_path = db_path
        self._init_db()
        self._create_session()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discovery_sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT,
                finished_at TEXT,
                duration_seconds REAL,
                companies_scanned INTEGER DEFAULT 0,
                connectors_executed INTEGER DEFAULT 0,
                jobs_returned INTEGER DEFAULT 0,
                jobs_verified INTEGER DEFAULT 0,
                new_companies INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                api_calls INTEGER DEFAULT 0,
                credits_consumed REAL DEFAULT 0,
                relevant_opportunities_produced INTEGER DEFAULT 0,
                avg_cost_per_opportunity REAL DEFAULT 0,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _create_session(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO discovery_sessions (session_id, started_at, status)
            VALUES (?, ?, 'RUNNING')
        ''', (self.session_id, self.started_at.isoformat()))
        conn.commit()
        conn.close()

    def log_metrics(self, companies_scanned=0, connectors_executed=0, jobs_returned=0, jobs_verified=0, new_companies=0, errors=0, warnings=0, api_calls=0, credits_consumed=0, relevant_opportunities_produced=0):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE discovery_sessions
            SET companies_scanned = companies_scanned + ?,
                connectors_executed = connectors_executed + ?,
                jobs_returned = jobs_returned + ?,
                jobs_verified = jobs_verified + ?,
                new_companies = new_companies + ?,
                errors = errors + ?,
                warnings = warnings + ?,
                api_calls = api_calls + ?,
                credits_consumed = credits_consumed + ?,
                relevant_opportunities_produced = relevant_opportunities_produced + ?
            WHERE session_id = ?
        ''', (companies_scanned, connectors_executed, jobs_returned, jobs_verified, new_companies, errors, warnings, api_calls, credits_consumed, relevant_opportunities_produced, self.session_id))
        conn.commit()
        conn.close()

    def finish(self, status: str = "SUCCESS"):
        finished_at = datetime.datetime.now()
        duration = (finished_at - self.started_at).total_seconds()
        
        # Calculate cost metrics before finishing
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT credits_consumed, relevant_opportunities_produced FROM discovery_sessions WHERE session_id = ?', (self.session_id,))
        row = cursor.fetchone()
        
        avg_cost = 0
        if row and row['relevant_opportunities_produced'] > 0:
            avg_cost = row['credits_consumed'] / row['relevant_opportunities_produced']
            
        cursor.execute('''
            UPDATE discovery_sessions
            SET finished_at = ?, duration_seconds = ?, status = ?, avg_cost_per_opportunity = ?
            WHERE session_id = ?
        ''', (finished_at.isoformat(), duration, status, avg_cost, self.session_id))
        conn.commit()
        conn.close()
