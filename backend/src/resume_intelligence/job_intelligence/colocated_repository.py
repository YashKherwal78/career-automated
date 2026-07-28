"""
Production Database-Co-located Job Intelligence Repository.

Updates normalized_jobs table directly with inline parsed jd_profile JSON, jd_hash, jd_version, and jd_parsed_at.
The jobs table is the SINGLE SOURCE OF TRUTH.
"""

import json
import time
import logging
from typing import Optional
from src.api.db import get_connection, is_postgres
from src.resume_intelligence.job_intelligence.models import StructuredJobProfile
from src.resume_intelligence.job_intelligence.parser import JobDescriptionParser

logger = logging.getLogger("ColocatedJobIntelligenceRepository")


class ColocatedJobIntelligenceRepository:
    """Co-locates parsed job intelligence directly inside the normalized_jobs database table."""

    def __init__(self):
        self.parser = JobDescriptionParser()

    def get_or_parse_job_intelligence(self, job_id: str, db_conn: Optional[Any] = None) -> Optional[StructuredJobProfile]:
        """Loads jd_profile directly from database row. If unparsed, parses once, updates DB, and returns."""
        def _execute_work(conn):
            if is_postgres():
                cursor = conn.execute(
                    "SELECT job_id, company_id, title, description, jd_profile, jd_hash FROM normalized_jobs WHERE job_id = %s",
                    (job_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT job_id, company_id, title, description, jd_profile, jd_hash FROM normalized_jobs WHERE job_id = ?",
                    (job_id,)
                )
            
            row = cursor.fetchone()
            if not row:
                logger.warning("Job %s not found in normalized_jobs table", job_id)
                return None

            # Unpack row values based on db driver
            if isinstance(row, dict):
                j_id, company_id, title, desc, jd_profile_json, jd_hash = (
                    row["job_id"], row["company_id"], row["title"], row["description"], row["jd_profile"], row["jd_hash"]
                )
            else:
                j_id, company_id, title, desc, jd_profile_json, jd_hash = row[0], row[1], row[2], row[3], row[4], row[5]

            # 1. Fast Path: Return cached jd_profile directly from DB column
            if jd_profile_json:
                try:
                    data = json.loads(jd_profile_json)
                    return StructuredJobProfile(**data)
                except Exception as e:
                    logger.error("Failed to parse stored jd_profile JSON for job %s: %s", job_id, e)

            # 2. Crawler/Ingestion Path: Parse JD once & co-locate directly in database table
            parsed_profile = self.parser.parse_job_description(
                job_id=j_id,
                company_name=company_id or "Company",
                role_title=title or "Software Engineer",
                raw_description=desc or ""
            )

            parsed_json = json.dumps(parsed_profile.model_dump())
            now = time.time()

            if is_postgres():
                conn.execute(
                    """
                    UPDATE normalized_jobs 
                    SET jd_profile = %s, jd_hash = %s, jd_version = 2, jd_parsed_at = %s, jd_parser = 'jie-parser-v2'
                    WHERE job_id = %s
                    """,
                    (parsed_json, parsed_profile.job_hash, now, j_id)
                )
            else:
                conn.execute(
                    """
                    UPDATE normalized_jobs 
                    SET jd_profile = ?, jd_hash = ?, jd_version = 2, jd_parsed_at = ?, jd_parser = 'jie-parser-v2'
                    WHERE job_id = ?
                    """,
                    (parsed_json, parsed_profile.job_hash, now, j_id)
                )

            conn.commit()
            logger.info("Co-located parsed jd_profile in normalized_jobs row for job %s", job_id)
            return parsed_profile

        if db_conn is not None:
            return _execute_work(db_conn)

        with get_connection() as conn:
            return _execute_work(conn)
