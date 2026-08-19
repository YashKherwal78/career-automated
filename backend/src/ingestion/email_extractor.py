import re
import time
from typing import List

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


_ROLE_AT_COMPANY_RE = re.compile(r"([A-Za-z0-9 /&+\-]+?)\s+(?:at|@|-)\s+([A-Za-z0-9 &.,'\-]+)")


def _parse_segment(segment: str):
    """Reads `Role at Company` / `Role - Company` out of the text immediately
    preceding an apply link. The LAST match in the segment wins: in a digest,
    the listing nearest the link is the one that link belongs to, while the
    first match is whatever job was listed before it."""
    text = _URL_RE.sub("", segment).strip()
    matches = list(_ROLE_AT_COMPANY_RE.finditer(text))
    if not matches:
        return "", ""
    match = matches[-1]
    return match.group(1).strip(), match.group(2).strip()


def _parse_email_body(body: str) -> List[dict]:
    """Best-effort parse of EVERY lead in the message body.

    This used to return only the first URL's lead. A job-alert email is
    almost always a digest listing several roles, so every job past the first
    was silently discarded -- and because the message was then marked
    processed, they were discarded permanently. Each URL now becomes its own
    lead, attributed from the text that precedes it. Returns [] when the body
    has no URL at all."""
    leads = []
    seen_urls = set()
    cursor = 0

    for match in _URL_RE.finditer(body):
        apply_link = match.group(0).rstrip(").,")
        segment = body[cursor:match.start()]
        cursor = match.end()

        if apply_link in seen_urls:
            continue
        seen_urls.add(apply_link)

        role, company = _parse_segment(segment)
        leads.append({"role": role, "company": company, "apply_link": apply_link})

    return leads


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

            parsed_leads = _parse_email_body(raw["body"])
            if not parsed_leads:
                # Deliberately NOT marked processed. Marking on failure burns
                # the message permanently: a later parser improvement could
                # extract it, but scan_job_alerts would never look at it
                # again. Leaving it unprocessed costs one cheap re-parse per
                # scan and keeps the message recoverable.
                logger.info(f"[email_extractor] no URL found in {raw['message_id']} -- leaving unprocessed for retry")
                continue

            extracted = 0
            for parsed in parsed_leads:
                lead = JobLead(
                    company=parsed["company"], role=parsed["role"], apply_link=parsed["apply_link"],
                    location=None, jd_excerpt=None, source="email", source_ref=raw["message_id"],
                )
                if lead.is_valid():
                    leads.append(lead)
                    extracted += 1
                else:
                    logger.info(f"[email_extractor] incomplete parse for {raw['message_id']}: {parsed}")

            if extracted:
                _mark_processed(conn, raw["message_id"], raw["sender"], raw["subject"])
            else:
                logger.info(
                    f"[email_extractor] {raw['message_id']} had {len(parsed_leads)} link(s) but no "
                    f"complete lead -- leaving unprocessed for retry"
                )

    return leads
