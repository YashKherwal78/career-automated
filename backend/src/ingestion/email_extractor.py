import re
import time
from typing import List, Optional

from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres
from src.integrations.email_listener import EmailListener
from src.ingestion.job_lead import JobLead

logger = setup_logger("email_extractor")

DEFAULT_SENDER_ALLOWLIST = [
    "jobs-noreply@linkedin.com",
    "jobalerts-noreply@linkedin.com",
    "noreply@indeed.com",
    "noreply@glassdoor.com",
]

_URL_RE = re.compile(r"https?://\S+")


def _parse_email_body(body: str) -> Optional[dict]:
    """Best-effort parse: first URL in the body is the apply link; company/
    role are read from `Role at Company` or `Role - Company` patterns in the
    body text. Returns None if no URL is found at all."""
    urls = _URL_RE.findall(body)
    if not urls:
        return None
    apply_link = urls[0].rstrip(").,")

    role, company = "", ""
    text_without_urls = _URL_RE.sub("", body).strip()
    match = re.search(r"([A-Za-z0-9 /&+\-]+?)\s+(?:at|@|-)\s+([A-Za-z0-9 &.,'\-]+)", text_without_urls)
    if match:
        role, company = match.group(1).strip(), match.group(2).strip()

    return {"role": role, "company": company, "apply_link": apply_link}


def _is_processed(conn, message_id: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    cur = conn.execute(f"SELECT message_id FROM processed_job_alert_emails WHERE message_id = {ph}", (message_id,))
    return cur.fetchone() is not None


def _mark_processed(conn, message_id: str, sender: str, subject: str):
    ph = "%s" if is_postgres() else "?"
    conn.execute(
        f"INSERT INTO processed_job_alert_emails (message_id, sender, subject, processed_at) VALUES ({ph}, {ph}, {ph}, {ph})",
        (message_id, sender, subject, time.time()),
    )
    conn.commit()


def scan_job_alerts(sender_allowlist: List[str] = None, since_days: int = 3) -> List[JobLead]:
    allowlist = sender_allowlist or DEFAULT_SENDER_ALLOWLIST
    listener = EmailListener()
    raw_emails = listener.search_job_alerts(allowlist, since_days=since_days)

    leads = []
    with get_connection() as conn:
        for raw in raw_emails:
            if _is_processed(conn, raw["message_id"]):
                continue

            parsed = _parse_email_body(raw["body"])
            if parsed:
                lead = JobLead(
                    company=parsed["company"], role=parsed["role"], apply_link=parsed["apply_link"],
                    location=None, jd_excerpt=None, source="email", source_ref=raw["message_id"],
                )
                if lead.is_valid():
                    leads.append(lead)
                else:
                    logger.info(f"[email_extractor] incomplete parse for {raw['message_id']}: {parsed}")
            else:
                logger.info(f"[email_extractor] no URL found in {raw['message_id']}")

            _mark_processed(conn, raw["message_id"], raw["sender"], raw["subject"])

    return leads
