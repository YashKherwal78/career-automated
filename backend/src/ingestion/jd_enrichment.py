import asyncio
import dataclasses
import time
import uuid

import httpx

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


# Cap on how much page text is kept as the JD excerpt. QuestionEngine folds
# this straight into an LLM prompt, so an unbounded scrape would blow the
# context window on a page that happens to be a 200KB careers portal.
_MAX_JD_CHARS = 8000


def _fetch_visible_text(url: str) -> str:
    """Lightweight fetch + visible-text extraction of a candidate JD page.

    Deliberately httpx + BeautifulSoup rather than Playwright: this runs from
    the ingestion pipeline, which has no browser context of its own, and a
    JD page that only renders under JS is not worth spinning up a browser for
    as a *third* fallback."""
    try:
        response = httpx.get(
            url,
            timeout=10.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; job-lead-enricher/1.0)"},
        )
    except Exception as e:
        logger.info(f"[jd_enrichment] could not fetch {url}: {e}")
        return ""

    if getattr(response, "status_code", None) != 200:
        return ""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
    except Exception as e:
        logger.info(f"[jd_enrichment] could not parse {url}: {e}")
        return ""

    lines = [ln.strip() for ln in text.splitlines()]
    cleaned = "\n".join(ln for ln in lines if ln)
    return cleaned[:_MAX_JD_CHARS]


def enrich_with_web_search(lead: JobLead) -> JobLead:
    """Last-resort JD enrichment (spec §2 step 3) -- only called after both
    the internal DB match and the Google Form's own description text have
    come up empty, to minimize paid/rate-limited search calls.

    This used to store the literal string "(found via web search: <url>)" as
    the excerpt. That is not a job description: downstream, jd_excerpt is fed
    to QuestionEngine as prose context for answer generation, so the LLM was
    being handed a URL-shaped sentence and told it was the JD. Now the found
    URL is actually fetched and its visible text extracted; if that fails,
    the lead is returned WITHOUT a jd_excerpt, so "no JD" stays honestly
    representable as empty rather than as a plausible-looking placeholder."""
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

    text = _fetch_visible_text(urls[0])
    if not text:
        logger.info(f"[jd_enrichment] no usable JD text at {urls[0]}")
        return lead

    logger.info(f"[jd_enrichment] extracted {len(text)} chars of JD text from {urls[0]}")
    return dataclasses.replace(lead, jd_excerpt=text)


def record_lead(
    lead: JobLead,
    user_id: str,
    connector,
    jd_source: str,
    result_status: str,
    really_submitted: bool,
    execution_run_id: str,
) -> None:
    """Write the terminal outcome of one lead into `ingested_job_leads`.

    This is the other half of already_applied(): the table was created and
    read from, but nothing ever inserted into it, so deduplication was a
    permanent no-op and a `--live` re-run of the same screenshot folder would
    happily resubmit every application. Never raises -- an audit/dedup write
    failing must not take down a run that already reached a terminal state."""
    ph = "%s" if is_postgres() else "?"
    try:
        with get_connection() as conn:
            conn.execute(
                f"""
                INSERT INTO ingested_job_leads
                    (id, user_id, company, role, apply_link, source, source_ref,
                     connector, jd_source, result_status, really_submitted,
                     execution_run_id, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
                """,
                (
                    str(uuid.uuid4()), user_id, lead.company, lead.role, lead.apply_link,
                    lead.source, lead.source_ref, connector, jd_source, result_status,
                    1 if really_submitted else 0, execution_run_id, time.time(),
                ),
            )
            conn.commit()
    except Exception as e:
        logger.info(f"[jd_enrichment] could not record lead {lead.company}/{lead.role}: {e}")
