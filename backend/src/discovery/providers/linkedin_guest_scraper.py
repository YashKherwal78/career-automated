"""
Free LinkedIn job search via LinkedIn's own public, unauthenticated
"jobs-guest" endpoints -- the same endpoints LinkedIn serves to logged-out
browsers/search engines for SEO, not a reverse-engineered internal API and
not a third-party scraping service. No login, no cookies, no Apify credits.

Two endpoints:
  - seeMoreJobPostings/search -- paginated search-results HTML (job cards:
    id, title, company, location, posted date, public URL).
  - jobPosting/{job_id} -- single job's full description HTML.

This is the same technique the "Junie AI" sibling project
(Auto-mail-all-branches/main/backend/utils/scraper.py) uses for single-URL
job extraction; this module extends it to cover search too, which is what
LinkedInJobsProvider actually needs (Junie's version only handles a job
already-in-hand, not "search for jobs matching X").

Confirmed live (2026-08-20): both endpoints return real, current job data
with a plain requests.get() and a spoofed desktop User-Agent -- no proxy
rotation, no browser automation. That's also this module's main risk: it's
scraping a public page LinkedIn's own ToS prohibits programmatic access to,
and LinkedIn can rate-limit/block this User-Agent or change the HTML
structure at any time without notice. Callers should treat a failure here
as "try the paid Apify path instead," not as a hard error -- see
LinkedInJobsProvider._discover_jobs_internal.
"""
from __future__ import annotations

import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from src.system.logger import setup_logger

logger = setup_logger("linkedin_guest_scraper")

_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Per-call delay between the search request and any detail requests that
# follow it -- polite pacing, not a proxy-rotation defense; a real
# anti-block strategy is out of scope for this free path, which is exactly
# why the paid Apify path stays available as a fallback.
_REQUEST_DELAY_SECONDS = 0.6


class LinkedInGuestBlocked(Exception):
    """Raised when the guest endpoint returns something that isn't a normal
    result page (non-200, CAPTCHA/login-wall redirect, empty/malformed
    HTML) -- signals the caller to fall back to Apify rather than treat
    zero results as "no jobs matched"."""


def search_jobs(
    keywords: str,
    location: str,
    f_e: str = "",
    f_tpr: str = "",
    start: int = 0,
    max_results: int = 25,
    timeout: int = 15,
) -> list[dict]:
    """Returns a list of {job_id, title, company, location, link, posted_at}
    dicts, best-effort truncated to max_results. Raises LinkedInGuestBlocked
    if the endpoint didn't return a parseable result page at all."""
    params = {"keywords": keywords, "location": location, "start": start}
    if f_e:
        params["f_E"] = f_e
    if f_tpr:
        params["f_TPR"] = f_tpr

    try:
        resp = requests.get(_SEARCH_URL, headers=_HEADERS, params=params, timeout=timeout)
    except requests.RequestException as e:
        raise LinkedInGuestBlocked(f"request failed: {e}") from e

    if resp.status_code != 200:
        raise LinkedInGuestBlocked(f"unexpected status {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("li div.base-card")
    if not cards and "jobPosting" not in resp.text and "base-card" not in resp.text:
        # Neither job cards nor any recognizable marker -- most likely a
        # block/redirect page rather than a genuine "0 results" response.
        raise LinkedInGuestBlocked("no recognizable job cards in response")

    jobs = []
    for card in cards[:max_results]:
        entity_urn = card.get("data-entity-urn", "")
        job_id = entity_urn.split(":")[-1] if entity_urn else ""
        title_el = card.select_one(".sr-only")
        company_el = card.select_one("h4.base-search-card__subtitle")
        loc_el = card.select_one(".job-search-card__location")
        link_el = card.select_one("a.base-card__full-link")
        time_el = card.select_one("time")

        jobs.append({
            "job_id": job_id,
            "title": title_el.get_text(strip=True) if title_el else "",
            "company": company_el.get_text(strip=True) if company_el else "",
            "location": loc_el.get_text(strip=True) if loc_el else "",
            "link": (link_el.get("href", "").split("?")[0] if link_el else ""),
            "posted_at": time_el.get("datetime") if time_el else "",
        })

    return [j for j in jobs if j["job_id"] and j["title"]]


def fetch_job_description(job_id: str, timeout: int = 15) -> str:
    """Best-effort full JD text for a job_id from search_jobs(); returns ""
    (never raises) since a missing description shouldn't drop an otherwise
    good search result -- callers already have title/company/location/link
    without this."""
    if not job_id:
        return ""
    try:
        resp = requests.get(_DETAIL_URL.format(job_id=job_id), headers=_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        desc = soup.select_one(".show-more-less-html__markup, .description__text")
        return desc.get_text(" ", strip=True) if desc else ""
    except requests.RequestException as e:
        logger.info(f"[linkedin_guest_scraper] description fetch failed for job_id={job_id}: {e}")
        return ""


# Matches every real-world shape a candidate might paste, in order of how
# specific/reliable the match is:
#   /jobs/view/software-engineer-at-acme-1234567890
#   /jobs/view/1234567890
#   ?currentJobId=1234567890 (search-results deep link)
_JOB_ID_URL_PATTERNS = (
    re.compile(r"/jobs/view/(?:[\w-]*-)?(\d{6,})"),
    re.compile(r"[?&]currentJobId=(\d{6,})"),
)


def extract_job_id_from_url(url: str) -> str:
    """Pulls the numeric job posting ID out of a pasted LinkedIn job URL, in
    whatever shape a candidate actually copies from their browser (full
    "/jobs/view/<slug>-<id>" pages and the "?currentJobId=" deep-link format
    search results use both appear in practice). Returns "" (never raises)
    on anything that doesn't look like a LinkedIn job URL -- the caller
    already needs to handle "couldn't read that page" as a normal, expected
    outcome, same as fetch_job_description above."""
    if not url:
        return ""
    for pattern in _JOB_ID_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)
    return ""


def fetch_job_posting_details(job_id: str, timeout: int = 15) -> dict:
    """Title/company/description for a single job_id from the same guest
    jobPosting page fetch_job_description already uses -- one request, not
    a separate one per field. Returns {} (never raises) if the job_id is
    empty or the page didn't come back in a recognizable shape (blocked,
    removed posting, layout change), so a caller can treat "couldn't read
    this job" as a normal, expected outcome rather than a crash."""
    if not job_id:
        return {}
    try:
        resp = requests.get(_DETAIL_URL.format(job_id=job_id), headers=_HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return {}
        soup = BeautifulSoup(resp.text, "html.parser")
        desc_el = soup.select_one(".show-more-less-html__markup, .description__text")
        title_el = soup.select_one(".top-card-layout__title, .topcard__title")
        company_el = soup.select_one(".topcard__org-name-link, .top-card-layout__second-subline a, .topcard__flavor")
        description = desc_el.get_text(" ", strip=True) if desc_el else ""
        if not description:
            # No recognizable description at all -- most likely a removed/
            # expired posting or a block page, not a genuinely empty JD.
            return {}
        return {
            "title": title_el.get_text(strip=True) if title_el else "",
            "company": company_el.get_text(strip=True) if company_el else "",
            "description": description,
        }
    except requests.RequestException as e:
        logger.info(f"[linkedin_guest_scraper] posting details fetch failed for job_id={job_id}: {e}")
        return {}


def search_jobs_with_descriptions(
    keywords: str,
    location: str,
    f_e: str = "",
    f_tpr: str = "",
    max_results: int = 25,
    fetch_descriptions: bool = True,
) -> list[dict]:
    """search_jobs() plus a "description" field per result, fetched with a
    small delay between requests. Single page only (start=0) -- pagination
    isn't needed at the volumes LinkedInJobsProvider requests today."""
    jobs = search_jobs(keywords, location, f_e=f_e, f_tpr=f_tpr, max_results=max_results)
    if not fetch_descriptions:
        return jobs
    for job in jobs:
        time.sleep(_REQUEST_DELAY_SECONDS)
        job["description"] = fetch_job_description(job["job_id"])
    return jobs
