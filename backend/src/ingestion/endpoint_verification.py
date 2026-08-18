import time
from typing import Optional

from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres

logger = setup_logger("endpoint_verification")


def is_endpoint_verified(company_domain: str, ats_type: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT status FROM ats_registry WHERE company_domain = {ph} AND ats_type = {ph}",
            (company_domain, ats_type),
        )
        row = cur.fetchone()
        if not row:
            return False
        status = row["status"] if hasattr(row, "keys") else row[0]
        return status == "VERIFIED"


def mark_endpoint_verified(company_domain: str, ats_type: str, endpoint: str) -> None:
    ph = "%s" if is_postgres() else "?"
    now = time.time()
    with get_connection() as conn:
        cur = conn.execute(
            f"SELECT id FROM ats_registry WHERE company_domain = {ph} AND ats_type = {ph}",
            (company_domain, ats_type),
        )
        existing = cur.fetchone()
        if existing:
            row_id = existing["id"] if hasattr(existing, "keys") else existing[0]
            conn.execute(
                f"UPDATE ats_registry SET status = {ph}, last_verified = {ph}, endpoint = {ph} WHERE id = {ph}",
                ("VERIFIED", now, endpoint, row_id),
            )
        else:
            conn.execute(
                f"""
                INSERT INTO ats_registry (company_domain, ats_type, endpoint, status, last_verified, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (company_domain, ats_type, endpoint, "VERIFIED", now, now),
            )
        conn.commit()
    logger.info(f"[endpoint_verification] marked {ats_type} endpoint verified for {company_domain}")
