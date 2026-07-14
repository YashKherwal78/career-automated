import logging
from typing import Any
from pydantic import BaseModel
from src.api.db import get_connection

logger = logging.getLogger(__name__)

class ConfidenceFormula:
    """Additive scoring for endpoint candidates."""
    
    # Base source weights
    SOURCE_WEIGHTS = {
        'MANUAL': 80,
        'EXISTING_DATASET': 40,
        'KNOWN_PATTERN': 30,
        'SEARCH_ENGINE': 20,
        'FIRECRAWL': 15,
        'META_TAGS': 10,
        'REGEX': 10,
        'REDIRECT': 5,
        'SITEMAP': 5,
        'ROBOTS_TXT': 5
    }
    
    @classmethod
    def calculate(
        cls,
        source: str,
        times_verified: int,
        times_failed: int,
        evidence: dict[str, Any] | None = None
    ) -> int:
        """
        confidence = provider_weight + historical_success + freshness + evidence - historical_failures - penalties
        Returns a score clamped between 0 and 100.
        """
        base = cls.SOURCE_WEIGHTS.get(source, 0)
        
        # Historical Success adds up to 30 points
        success_bonus = min(times_verified * 5, 30)
        
        # Historical Failures subtract points
        failure_penalty = times_failed * 10
        
        # Evidence bonus (e.g. high search rank, explicit anchor text)
        evidence_bonus = 0
        if evidence:
            if evidence.get('search_rank', 99) <= 3:
                evidence_bonus += 10
            if "careers" in str(evidence.get('anchor_text', '')).lower():
                evidence_bonus += 5
                
        score = base + success_bonus + evidence_bonus - failure_penalty
        return max(0, min(100, score))


class EndpointIntelligenceService:
    """Centralized service for managing confidence, health, and history of ATS endpoints."""
    
    @staticmethod
    def log_registry_change(
        conn,
        company_id: str,
        provider_id: str,
        old_endpoint_url: str | None,
        new_endpoint_url: str,
        reason: str
    ):
        from src.api.db import is_postgres
        cursor = conn.cursor()
        q = """
            INSERT INTO registry_history (company_id, provider_id, old_endpoint_url, new_endpoint_url, reason)
            VALUES (%s, %s, %s, %s, %s)
            """
        if not is_postgres():
            q = q.replace("%s", "?")
        cursor.execute(q, (company_id, provider_id, old_endpoint_url, new_endpoint_url, reason))

    @staticmethod
    def report_verification_success(company_id: str, provider_id: str, url: str):
        """Called when an endpoint candidate is successfully verified by an ATSDetector."""
        from src.api.db import is_postgres
        conn = get_connection()
        try:
            now = 'now()' if is_postgres() else "datetime('now')"
            
            # Update the candidate's metrics
            q = f"""
                UPDATE endpoint_candidates
                SET times_verified = times_verified + 1,
                    last_verified = {now},
                    lifecycle_state = 'VERIFIED'
                WHERE company_id = %s AND provider_id = %s AND url = %s
            """
            if not is_postgres():
                q = q.replace("%s", "?")
            params = (company_id, provider_id, url)
            
            cursor = conn.cursor()
            cursor.execute(q, params)
            
            # Recalculate confidence
            q_conf = "SELECT discovery_source, times_verified, times_failed, evidence FROM endpoint_candidates WHERE company_id = %s AND provider_id = %s AND url = %s"
            if not is_postgres():
                q_conf = q_conf.replace("%s", "?")
            cursor.execute(q_conf, params)
            row = cursor.fetchone()
            if row:
                import json
                try:
                    evidence = json.loads(row[3]) if isinstance(row[3], str) else row[3]
                except Exception:
                    evidence = {}
                new_conf = ConfidenceFormula.calculate(row[0], row[1], row[2], evidence)
                q_upd = "UPDATE endpoint_candidates SET confidence_score = %s WHERE company_id = %s AND provider_id = %s AND url = %s"
                if not is_postgres():
                    q_upd = q_upd.replace("%s", "?")
                cursor.execute(q_upd, (new_conf, company_id, provider_id, url))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error in report_verification_success: {e}")
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def report_verification_failure(company_id: str, provider_id: str, url: str, reason: str):
        """Called when an endpoint candidate fails verification (e.g. 404, invalid signature)."""
        from src.api.db import is_postgres
        conn = get_connection()
        try:
            now = 'now()' if is_postgres() else "datetime('now')"
            
            q = f"""
                UPDATE endpoint_candidates
                SET times_failed = times_failed + 1,
                    last_verified = {now},
                    lifecycle_state = CASE
                        WHEN times_failed >= 2 THEN 'REJECTED'
                        ELSE lifecycle_state
                    END
                WHERE company_id = %s AND provider_id = %s AND url = %s
            """
            if not is_postgres():
                q = q.replace("%s", "?")
            params = (company_id, provider_id, url)
            
            cursor = conn.cursor()
            cursor.execute(q, params)
            
            # Recalculate confidence
            q_conf = "SELECT discovery_source, times_verified, times_failed, evidence FROM endpoint_candidates WHERE company_id = %s AND provider_id = %s AND url = %s"
            if not is_postgres():
                q_conf = q_conf.replace("%s", "?")
            cursor.execute(q_conf, params)
            row = cursor.fetchone()
            if row:
                import json
                try:
                    evidence = json.loads(row[3]) if isinstance(row[3], str) else row[3]
                except Exception:
                    evidence = {}
                new_conf = ConfidenceFormula.calculate(row[0], row[1], row[2], evidence)
                q_upd = "UPDATE endpoint_candidates SET confidence_score = %s WHERE company_id = %s AND provider_id = %s AND url = %s"
                if not is_postgres():
                    q_upd = q_upd.replace("%s", "?")
                cursor.execute(q_upd, (new_conf, company_id, provider_id, url))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Error in report_verification_failure: {e}")
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def report_crawl_success(company_id: str, provider_id: str):
        """Called by JobCrawlerWorker after a successful sync."""
        conn = get_connection()
        try:
            now = 'now()' if hasattr(conn.cursor(), 'execute') else "datetime('now')"
            q = f"""
                UPDATE ats_registry
                SET success_count = success_count + 1,
                    last_success = {now},
                    health_score = LEAST(100, health_score + 5)
                WHERE company_id = %s AND provider_id = %s
            """
            if hasattr(conn.cursor(), 'execute'):
                conn.cursor().execute(q, (company_id, provider_id))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def report_crawl_failure(company_id: str, provider_id: str, reason: str, is_permanent: bool = False):
        """Called by JobCrawlerWorker after a sync fails."""
        conn = get_connection()
        try:
            now = 'now()' if hasattr(conn.cursor(), 'execute') else "datetime('now')"
            health_penalty = 50 if is_permanent else 10
            q = f"""
                UPDATE ats_registry
                SET failure_count = failure_count + 1,
                    last_failure = {now},
                    last_failure_reason = %s,
                    health_score = GREATEST(0, health_score - %s)
                WHERE company_id = %s AND provider_id = %s
            """
            if hasattr(conn.cursor(), 'execute'):
                conn.cursor().execute(q, (reason, health_penalty, company_id, provider_id))
            conn.commit()
        finally:
            conn.close()
