from src.system.logger import setup_logger
logger = setup_logger('discovery')
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
    
    logger.info(f"[{company_name}] Running Contact Discovery...")
    
    # Tier 1: Job Description Parsing
    jd_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', job_description)
    if jd_emails:
        logger.info(f"  -> Found {len(jd_emails)} email(s) in JD.")
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
    logger.info(f"  -> Falling back to DuckDuckGo X-Ray search...")
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
        
    # Tier 3 previously returned three hardcoded fake people ("Rahul
    # Sharma", "Sarah Johnson", "Mike Recruiter" with "-mock" LinkedIn
    # URLs) as if they were real discovered contacts — silently writing
    # fabricated people into the CRM (and, downstream, generating guessed
    # emails for them) whenever Tiers 1-2 found nothing.
    #
    # Replaced with a real (not fabricated) Tier 3: Hunter.io's own
    # domain-search doesn't need a person's name at all — it returns real
    # people AND their real emails directly from Hunter's own contact
    # database. Confirmed live: for a company where DuckDuckGo's LinkedIn
    # X-ray search (Tier 2) found nobody, Hunter's domain-search still
    # found a real HR contact with a real email
    # (sarthak.tibrewal@zomato.com for Zomato). This has no name to score
    # against, so it's treated as already-vetted (Hunter's own confidence
    # score stands in for the profile/referral scoring the other tiers
    # get) rather than run back through scrape_profile/score_contact.
    if Config.HUNTER_API_KEY:
        logger.info(f"  -> Falling back to Hunter.io domain-search for {company_name}...")
        from src.outreach.email_finder import find_email_hunter_domain, search_company_domain
        domain = search_company_domain(company_name, context=job_title)
        if domain:
            try:
                best_email, source, hunter_contacts = find_email_hunter_domain(domain, Config.HUNTER_API_KEY)
                for hc in hunter_contacts[:3]:
                    if not hc.get("name"):
                        continue
                    contacts.append({
                        "contact_name": hc["name"],
                        "job_title": hc.get("position") or "Unknown",
                        "company": company_name,
                        "linkedin_url": "",
                        "discovery_source": "Hunter.io Domain Search",
                        "contact_type": _infer_contact_type(hc.get("position") or hc.get("department") or ""),
                        "email": hc["email"],
                        "email_confidence": hc.get("confidence", 0),
                    })
            except RuntimeError:
                logger.info("  -> Hunter.io domain-search credits exhausted.")
            except Exception as e:
                logger.info(f"  -> Hunter.io domain-search error: {e}")

    if not contacts:
        logger.info(f"  -> No contacts found for {company_name} via JD parsing, DuckDuckGo, or Hunter.io.")
    return contacts

def _infer_contact_type(title: str) -> str:
    title_lower = title.lower()
    if "recruit" in title_lower or "talent" in title_lower or "hr" in title_lower:
        return "Recruiter"
    if "manager" in title_lower or "head" in title_lower or "vp" in title_lower or "director" in title_lower:
        return "Hiring Manager"
    return "Technical IC"
