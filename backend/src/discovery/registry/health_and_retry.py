from src.api.db import get_connection
import sqlite3
import datetime
from typing import Optional, List

class RetryManager:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_next_retry(self, retry_count: int) -> str:
        """Exponential backoff: 1hr -> 6hr -> 1day -> 7days"""
        now = datetime.datetime.utcnow()
        if retry_count == 0:
            delta = datetime.timedelta(hours=1)
        elif retry_count == 1:
            delta = datetime.timedelta(hours=6)
        elif retry_count == 2:
            delta = datetime.timedelta(days=1)
        else:
            delta = datetime.timedelta(days=7)
        return (now + delta).isoformat()

    def queue_discovery_retry(self, company_id: str, failure_reason: str):
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("SELECT retry_count FROM discovery_retry_queue WHERE company_id = ?", (company_id,))
        row = c.fetchone()
        
        if row:
            retry_count = row[0] + 1
            next_retry = self._get_next_retry(retry_count)
            c.execute('''
                UPDATE discovery_retry_queue 
                SET retry_count = ?, next_retry_at = ?, failure_reason = ? 
                WHERE company_id = ?
            ''', (retry_count, next_retry, failure_reason, company_id))
        else:
            next_retry = self._get_next_retry(0)
            c.execute('''
                INSERT INTO discovery_retry_queue (company_id, failure_reason, next_retry_at)
                VALUES (?, ?, ?)
            ''', (company_id, failure_reason, next_retry))
            
        conn.commit()
        conn.close()

    def queue_monitoring_retry(self, endpoint_id: str, failure_reason: str):
        conn = get_connection()
        c = conn.cursor()
        
        c.execute("SELECT retry_count FROM monitoring_retry_queue WHERE endpoint_id = ?", (endpoint_id,))
        row = c.fetchone()
        
        if row:
            retry_count = row[0] + 1
            next_retry = self._get_next_retry(retry_count)
            c.execute('''
                UPDATE monitoring_retry_queue 
                SET retry_count = ?, next_retry_at = ?, failure_reason = ? 
                WHERE endpoint_id = ?
            ''', (retry_count, next_retry, failure_reason, endpoint_id))
        else:
            next_retry = self._get_next_retry(0)
            c.execute('''
                INSERT INTO monitoring_retry_queue (endpoint_id, failure_reason, next_retry_at)
                VALUES (?, ?, ?)
            ''', (endpoint_id, failure_reason, next_retry))
            
        conn.commit()
        conn.close()

class HealthScorer:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def compute_health_score(self, endpoint_id: str, success_rate: float, avg_latency: float, recent_failures: int) -> float:
        """Computes a 0-100 score based on metrics."""
        score = 100.0
        
        # Penalize for low success rate (e.g. 95% = -5 points)
        score -= (1.0 - success_rate) * 100
        
        # Penalize for latency > 1000ms
        if avg_latency > 1000:
            score -= (avg_latency - 1000) / 100.0
            
        # Penalize for recent failures
        score -= (recent_failures * 5)
        
        return max(0.0, min(100.0, score))

    def update_endpoint_health(self, endpoint_id: str, success_rate: float, avg_latency: float, recent_failures: int):
        score = self.compute_health_score(endpoint_id, success_rate, avg_latency, recent_failures)
        
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE career_endpoints 
            SET endpoint_health_score = ?
            WHERE endpoint_id = ?
        ''', (score, endpoint_id))
        conn.commit()
        conn.close()
        return score
