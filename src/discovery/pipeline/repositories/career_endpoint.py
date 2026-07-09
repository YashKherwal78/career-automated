import sqlite3
from typing import Optional
from src.discovery.pipeline.repositories.base import BaseRepository

class CareerEndpointRepository(BaseRepository):
    def save_verification(self, result, connection: Optional[sqlite3.Connection] = None):
        """
        Updates status, health_status, confidence, failure_reason, and last_verified_at
        for a career endpoint. Accepts an optional connection to support active transactions.
        """
        db_status = "VERIFIED" if result.verified else "FAILED"
        health_status = "HEALTHY" if result.verified else "BROKEN"
        failure_reason = result.reason
        confidence = result.confidence
        endpoint_id = result.endpoint_id
        
        query = """
            UPDATE career_endpoints 
            SET status = ?, confidence = ?, health_status = ?, last_verified_at = CURRENT_TIMESTAMP, failure_reason = ?
            WHERE endpoint_id = ?
        """
        
        if connection:
            connection.execute(query, (db_status, confidence, health_status, failure_reason, endpoint_id))
        else:
            with self.get_connection() as conn:
                conn.execute(query, (db_status, confidence, health_status, failure_reason, endpoint_id))
                conn.commit()
