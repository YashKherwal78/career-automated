from typing import List, Dict, Any
from pydantic import BaseModel
from src.api.db import get_connection

class EndpointCandidate(BaseModel):
    candidate_id: str
    company_id: str
    provider_id: str
    url: str
    discovery_source: str
    confidence_score: int
    health_score: int
    lifecycle_state: str

class EndpointRankingEngine:
    """Ranks available candidates for a given company based on confidence score."""
    
    @staticmethod
    def get_ranked_candidates(company_id: str) -> List[EndpointCandidate]:
        """
        Retrieves all active or discovered candidates for a company, sorted by confidence.
        Does not return REJECTED or ARCHIVED candidates.
        """
        conn = get_connection()
        candidates = []
        try:
            cursor = conn.cursor()
            # In PostgreSQL, we can use dictionary-like access if configured, but let's use standard tuple access just in case.
            from src.api.db import is_postgres
            q = """
                SELECT candidate_id, company_id, provider_id, url, discovery_source, confidence_score, health_score, lifecycle_state
                FROM endpoint_candidates
                WHERE company_id = %s AND lifecycle_state IN ('DISCOVERED', 'VERIFIED', 'UNHEALTHY', 'ACTIVE')
                ORDER BY confidence_score DESC, last_seen DESC
                """
            if not is_postgres():
                q = q.replace("%s", "?")
            cursor.execute(q, (company_id,))
            for row in cursor.fetchall():
                if isinstance(row, dict):
                    candidates.append(EndpointCandidate(**row))
                else:
                    candidates.append(EndpointCandidate(
                        candidate_id=str(row[0]),
                        company_id=row[1],
                        provider_id=row[2],
                        url=row[3],
                        discovery_source=row[4],
                        confidence_score=row[5],
                        health_score=row[6],
                        lifecycle_state=row[7]
                    ))
        finally:
            conn.close()
            
        return candidates

