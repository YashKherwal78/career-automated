import re
from typing import Dict, Any

def extract_basic_info(title: str, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts job title, company, url, id, and ATS provider."""
    # Use title provided, or attempt to find it from headings
    job_title = title or ""
    if not job_title:
        title_match = re.search(r'(?:title|position|role):\s*(.*)', text, re.IGNORECASE)
        if title_match:
            job_title = title_match.group(1).strip()
            
    company = metadata.get("company") or ""
    if not company:
        company_match = re.search(r'(?:company|employer|organization):\s*(.*)', text, re.IGNORECASE)
        if company_match:
            company = company_match.group(1).strip()
            
    job_url = metadata.get("job_url") or ""
    job_id = metadata.get("job_id") or ""
    
    # Try to extract Job ID from URL or text
    if not job_id and job_url:
        id_match = re.search(r'/jobs?/(\d+)', job_url)
        if id_match:
            job_id = id_match.group(1)
            
    if not job_id:
        id_match = re.search(r'(?:job\s*id|requisition\s*id|req\s*id|job\s*number):\s*([a-zA-Z0-9_-]+)', text, re.IGNORECASE)
        if id_match:
            job_id = id_match.group(1).strip()
            
    # Determine ATS Provider
    ats_provider = "Unknown"
    if job_url:
        url_lower = job_url.lower()
        if "workday" in url_lower:
            ats_provider = "Workday"
        elif "greenhouse" in url_lower:
            ats_provider = "Greenhouse"
        elif "lever.co" in url_lower:
            ats_provider = "Lever"
        elif "jobvite" in url_lower:
            ats_provider = "Jobvite"
        elif "ashbyhq" in url_lower:
            ats_provider = "Ashby"
        elif "bamboohr" in url_lower:
            ats_provider = "BambooHR"
        elif "smartrecruiters" in url_lower:
            ats_provider = "SmartRecruiters"
            
    return {
        "title": job_title,
        "company": company,
        "job_url": job_url,
        "job_id": job_id,
        "ats_provider": ats_provider
    }
