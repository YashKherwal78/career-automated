import logging
from typing import Optional, Dict, Any
from src.crm.database import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ATSLearningEngine:
    """
    Maintains a learning cache for ATS detection to prevent deterministic, expensive scans.
    """
    
    @staticmethod
    def get_cached_ats(domain: str, min_confidence: float = 0.8) -> Optional[str]:
        """
        Consults the learning cache to see if we already know the ATS for this domain
        with a high enough confidence.
        """
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ats_provider, confidence FROM ats_learning_cache
            WHERE domain = ? AND confidence >= ?
        ''', (domain, min_confidence))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            logger.info(f"ATS Learning Engine hit for {domain}: {row['ats_provider']} (Confidence: {row['confidence']})")
            return row['ats_provider']
            
        return None
        
    @staticmethod
    def record_scan_result(domain: str, ats_provider: str, success: bool):
        """
        Records the outcome of an ATS job extraction to update historical confidence.
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT successful_extractions, failed_extractions FROM ats_learning_cache WHERE domain = ?", (domain,))
        row = cursor.fetchone()
        
        if row:
            successes = row[0] + (1 if success else 0)
            failures = row[1] + (0 if success else 1)
            total = successes + failures
            confidence = successes / total if total > 0 else 0.0
            
            cursor.execute('''
                UPDATE ats_learning_cache 
                SET ats_provider = ?, successful_extractions = ?, failed_extractions = ?, 
                    confidence = ?, last_seen = CURRENT_TIMESTAMP
                WHERE domain = ?
            ''', (ats_provider, successes, failures, confidence, domain))
        else:
            successes = 1 if success else 0
            failures = 0 if success else 1
            confidence = 1.0 if success else 0.0
            cursor.execute('''
                INSERT INTO ats_learning_cache (domain, ats_provider, successful_extractions, failed_extractions, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (domain, ats_provider, successes, failures, confidence))
            
        conn.commit()
        conn.close()
        
import sqlite3
