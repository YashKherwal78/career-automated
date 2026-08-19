import asyncio
import dataclasses
from typing import Optional

from src.system.logger import setup_logger
from src.api.db import get_connection, is_postgres
from src.ingestion.job_lead import JobLead
from src.discovery.providers.search_engine_provider import YahooBackend

logger = setup_logger("jd_enrichment")


def enrich(lead: JobLead, repos=None) -> JobLead:
    """Step 1 only: internal DB match. Steps 2 (form description) and 3
    (web search) are applied later in the pipeline by callers that have
    the capabilities this function doesn't (see pipeline.py)."""
    if lead.jd_excerpt:
        return lead

    if repos is None:
        from src.core.repositories.manager import RepositoryManager
        repos = RepositoryManager()

    jobs = repos.job.get_jobs(company=lead.company, title=lead.role, page_size=1)
    if not jobs:
        return lead

    description = jobs[0].get("description")
    if not description:
        return lead

    return dataclasses.replace(lead, jd_excerpt=description)


def already_applied(lead: JobLead, user_id: str) -> bool:
    ph = "%s" if is_postgres() else "?"
    with get_connection() as conn:
        cur = conn.execute(
            f"""
            SELECT id FROM ingested_job_leads
            WHERE user_id = {ph} AND company = {ph} AND role = {ph} AND really_submitted = 1
            """,
            (user_id, lead.company, lead.role),
        )
        return cur.fetchone() is not None


def enrich_with_web_search(lead: JobLead) -> JobLead:
    """Last-resort JD enrichment (spec §2 step 3) -- only called by the
    pipeline after both the internal DB match and the Google Form's own
    description text have come up empty, to minimize paid/rate-limited
    search calls."""
    if lead.jd_excerpt:
        return lead

    backend = YahooBackend()
    query = f"{lead.company} {lead.role} job description"
    try:
        urls = asyncio.run(backend.search(query))
    except Exception as e:
        logger.info(f"[jd_enrichment] web search failed for {query}: {e}")
        return lead

    if not urls:
        return lead

    # Storing the found URL as the excerpt seed is deliberately conservative
    # here -- fetching and extracting full page text is Task 8/10's
    # GoogleFormsHandler's territory (it already has an HTTP-capable
    # Playwright context); this function's job is only to decide whether a
    # plausible JD source exists at all, not to scrape it.
    return dataclasses.replace(lead, jd_excerpt=f"(found via web search: {urls[0]})")
