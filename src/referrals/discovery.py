import requests
import re
from typing import List, Dict
from src.config.config import Config

def discover_contacts(company_name: str, job_title: str, job_description: str = "") -> List[Dict]:
    """
    Phase 1 - Contact Discovery (Safe Job Discovery Architecture)
    Order:
    1. JD Parsing
    2. DuckDuckGo X-Ray
    3. Apify/Apollo fallback (mocked for now)
    """
    contacts = []
    
    print(f"[{company_name}] Running Contact Discovery...")
    
    # Tier 1: Job Description Parsing
    jd_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', job_description)
    if jd_emails:
        print(f"  -> Found {len(jd_emails)} email(s) in JD.")
        for email in set(jd_emails):
            contacts.append({
                "contact_name": email.split('@')[0].capitalize(),
                "job_title": "Job Poster",
                "company": company_name,
                "linkedin_url": f"email_contact_{email}",
                "discovery_source": "Job Description",
                "contact_type": "Recruiter",
                "email": email
            })
            
    if contacts:
        return contacts
        
    # Tier 2: DuckDuckGo Search
    print(f"  -> Falling back to DuckDuckGo X-Ray search...")
    from src.search.duckduckgo_provider import DuckDuckGoProvider
    ddg = DuckDuckGoProvider()
    
    # Try finding recruiters
    recruiters = ddg.search_recruiters(company_name)
    if recruiters:
        contacts.extend(recruiters)
        
    # Try finding hiring managers
    hms = ddg.search_hiring_managers(company_name, job_title)
    if hms:
        contacts.extend(hms)
        
    if contacts:
        return contacts
        
    # Tier 3: Apify Fallback (Mocked since credits are empty)
    print(f"  -> Falling back to Apify (Mocked for safety)...")
    contacts = [
        {"contact_name": "Rahul Sharma", "job_title": "Machine Learning Engineer", "company": company_name, "linkedin_url": "https://linkedin.com/in/rahul-sharma-mock", "discovery_source": "Apify Fallback", "contact_type": "Technical IC"},
        {"contact_name": "Sarah Johnson", "job_title": "Engineering Manager", "company": company_name, "linkedin_url": "https://linkedin.com/in/sarah-mock", "discovery_source": "Apify Fallback", "contact_type": "Hiring Manager"},
        {"contact_name": "Mike Recruiter", "job_title": "Technical Recruiter", "company": company_name, "linkedin_url": "https://linkedin.com/in/mike-recruiter-mock", "discovery_source": "Apify Fallback", "contact_type": "Recruiter"}
    ]
    
    return contacts

def _infer_contact_type(title: str) -> str:
    title_lower = title.lower()
    if "recruit" in title_lower or "talent" in title_lower or "hr" in title_lower:
        return "Recruiter"
    if "manager" in title_lower or "head" in title_lower or "vp" in title_lower or "director" in title_lower:
        return "Hiring Manager"
    return "Technical IC"
