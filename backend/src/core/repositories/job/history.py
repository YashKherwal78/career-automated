from typing import Optional, Dict, Any
from src.core.repositories.base import BaseRepository

class CrawlHistoryRepository(BaseRepository):
    def insert_history(self, company_id: str, provider: str, metrics: Dict[str, Any], tx: Optional[Any] = None) -> None:
        conn = tx if tx else self.get_connection()
        try:
            conn.execute("""
                INSERT INTO company_crawl_history (
                    company_id, provider, duration, status, jobs_found, error, session_id,
                    crawl_event_id, jobs_inserted, jobs_updated, jobs_archived,
                    crawl_duration_ms, response_status, provider_latency_ms,
                    parser_version, connector_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                company_id, provider, metrics.get('duration'), metrics.get('status'),
                metrics.get('jobs_found'), metrics.get('error'), metrics.get('session_id'),
                metrics.get('crawl_event_id'), metrics.get('jobs_inserted', 0),
                metrics.get('jobs_updated', 0), metrics.get('jobs_archived', 0),
                metrics.get('crawl_duration_ms'), metrics.get('response_status'),
                metrics.get('provider_latency_ms'), metrics.get('parser_version'),
                metrics.get('connector_version')
            ))
            if not tx:
                conn.commit()
        finally:
            if not tx:
                conn.close()
