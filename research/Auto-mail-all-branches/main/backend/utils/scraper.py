from __future__ import annotations
import logging
import os
import re
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

from utils.email_finder import find_recruiter_email

logger = logging.getLogger(__name__)

def parse_job_url(url: str, api_keys: dict = None) -> dict:
    """Parse a LinkedIn job URL and extract key details."""
    api_keys = api_keys or {}
    try:
        # Extract job ID
        match = re.search(r'view/(\d+)|jobPosting/(\d+)|currentJobId=(\d+)|-(\d{8,11})\b', url)
        
        if match:
            job_id = match.group(1) or match.group(2) or match.group(3) or match.group(4)
        else:
            job_id = None
            
        if not job_id:
             logger.error(f"Could not extract LinkedIn job ID from URL: {url}")
             return {}

        api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(api_url, headers=headers, timeout=10)
        if res.status_code != 200:
             logger.error(f"Failed to fetch LinkedIn job API. Status: {res.status_code}")
             return {}

        soup = BeautifulSoup(res.text, "html.parser")
        
        # We don't want to lose spaces between tags, so we separator=' '
        raw_text = soup.get_text(separator=' ', strip=True)
        if not raw_text:
             logger.warning("No description found in LinkedIn HTML. Ensure it is a valid LinkedIn Job ID.")
        
        from utils.llm import extract_job_details
        parsed_data = extract_job_details(raw_text, api_keys=api_keys)

        job_data = {
            "company_name": parsed_data.get("company_name"),
            "job_title": parsed_data.get("job_title"),
            "job_description": parsed_data.get("job_description"),
            "recruiter_email": parsed_data.get("recruiter_email"),
            "recruiter_name": parsed_data.get("recruiter_name"),
            "company_website": parsed_data.get("company_website") or "",
        }
        return job_data
    except Exception as e:
        logger.error(f"Error parsing job URL: {e}")
        return {}

def research_company(company_name: str) -> str:
    """Fetch lightweight company research using DuckDuckGo."""
    if not company_name:
        return ""
    try:
        results = DDGS().text(f"{company_name} company overview operations industry summary", max_results=3)
        if not results:
            return ""
        
        snippets = [r.get('body', '').strip() for r in results if r.get('body')]
        return " | ".join(snippets)
    except Exception as e:
        logger.error(f"Error researching company {company_name}: {e}")
        return ""


def search_company_domain(company_name: str, context: str = "") -> str:
    """Search for a company's official website domain via DuckDuckGo.
    
    Returns a bare domain like 'mindenious.com' or '' if not found.
    """
    if not company_name:
        return ""
    try:
        query = f'"{company_name}" official website'
        if context:
            # Inject context (like job title) to disambiguate collisions (e.g. Fini candy vs Fini AI)
            query = f'"{company_name}" {context} official website'
            
        results = DDGS().text(query, max_results=5)
        if not results:
            return ""

        import re
        # Look for a likely company domain from the search result URLs
        for r in results:
            href = r.get("href", "") or r.get("url", "")
            if not href:
                continue
            # Strip scheme + www
            cleaned = re.sub(r"^https?://", "", href.strip()).lstrip("www.")
            domain = cleaned.split("/")[0]
            # Skip search engines, social media, job boards, etc.
            skip_domains = {
                "linkedin.com", "facebook.com", "twitter.com", "x.com",
                "instagram.com", "youtube.com", "github.com",
                "wikipedia.org", "glassdoor.com", "indeed.com",
                "naukri.com", "ambitionbox.com", "crunchbase.com",
                "zoominfo.com", "google.com", "bing.com",
                "trustpilot.com", "capterra.com", "g2.com",
            }
            
            # Subdomain-aware skipping
            is_skipped = any(domain == skip or domain.endswith("." + skip) for skip in skip_domains)
            
            if domain and not is_skipped and "." in domain:
                logger.info(f"[Scraper] Inferred company domain for '{company_name}': {domain}")
                return domain
        
        logger.info(f"[Scraper] Could not infer domain for '{company_name}' from search results.")
        return ""
    except Exception as e:
        logger.error(f"[Scraper] Error searching company domain for {company_name}: {e}")
        return ""


def enrich_recruiter_email(
    job_data: dict,
    additional_context: str = "",
    hunter_api_key: str = "",
    getprospect_api_key: str = "",
    apollo_api_key: str = "",
    snov_api_key: str = "",
    progress_log: list | None = None,
) -> tuple[str | None, str, list[dict]]:
    """
    Convenience wrapper: run the cascading email finder using data already
    extracted from a job posting.

    Returns (email, source_label, all_contacts).
    """
    # If an email was already extracted by LLM from the JD, trust it first
    if job_data.get("recruiter_email"):
        logger.info(f"[Enrich] Using email already in job_data: {job_data['recruiter_email']}")
        if progress_log is not None:
            progress_log.append(("✅", f"Email found in JD data: {job_data['recruiter_email']}"))
        return job_data["recruiter_email"], "jd_text", [{"email": job_data["recruiter_email"], "name": job_data.get("recruiter_name", ""), "position": "", "department": "", "confidence": 100, "source": "jd_text"}]

    # Resolve domain: use company_website if available, otherwise infer via search
    company_website = job_data.get("company_website", "")
    company_domain = ""

    if company_website:
        import re
        cleaned = re.sub(r"^https?://", "", company_website.strip()).lstrip("www.")
        company_domain = cleaned.split("/")[0]
    
    if not company_domain and job_data.get("company_name"):
        logger.info(f"[Enrich] No company website in JD — searching for domain of '{job_data['company_name']}'...")
        if progress_log is not None:
            progress_log.append(("🔎", f"No website in JD — inferring domain for '{job_data['company_name']}'..."))
        
        # Use job_title as context to heavily disambiguate generic names
        company_domain = search_company_domain(
            job_data["company_name"], 
            context=job_data.get("job_title", "")
        )
        
        if company_domain and progress_log is not None:
            progress_log.append(("✅", f"Inferred domain: {company_domain}"))

    return find_recruiter_email(
        jd_text=job_data.get("job_description", ""),
        additional_context=additional_context,
        recruiter_name=job_data.get("recruiter_name", ""),
        company_website=company_website,
        company_domain=company_domain,
        hunter_api_key=hunter_api_key,
        getprospect_api_key=getprospect_api_key,
        apollo_api_key=apollo_api_key,
        snov_api_key=snov_api_key,
        progress_log=progress_log,
    )


