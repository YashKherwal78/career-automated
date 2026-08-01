import logging
import re
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

def parse_job_url(url: str) -> dict:
    """Parse a LinkedIn job URL and extract key details."""
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
        parsed_data = extract_job_details(raw_text)

        return {
            "company_name": parsed_data.get("company_name"),
            "job_title": parsed_data.get("job_title"),
            "job_description": parsed_data.get("job_description"),
            "recruiter_email": parsed_data.get("recruiter_email"),
            "recruiter_name": parsed_data.get("recruiter_name")
        }
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
