from src.system.logger import setup_logger
logger = setup_logger('email_discovery')
from src.config.config import Config
from src.outreach.email_finder import find_recruiter_email
from typing import Tuple, Optional


def discover_email(contact_name: str, company_name: str, job_title: str = "", company_domain: str = "") -> Tuple[Optional[str], int]:
    """
    Real cascading email lookup (Hunter -> GetProspect -> Apollo -> Snov.io,
    with DuckDuckGo domain inference when no company website is known).

    Previously this fell back to a FABRICATED guess
    (f"{first}.{last}@{company}.com") with a fake confidence score of 30
    whenever no real API key found anything — silently writing an
    unverified, likely-wrong email into the CRM as if it were real data.
    That fallback is removed: returns (None, 0) when nothing genuine is
    found, matching this project's standing "never guess/fabricate"
    principle for any field with real-world consequences (here: emailing
    a made-up address on the candidate's behalf).
    """
    email, source, _ = find_recruiter_email(
        recruiter_name=contact_name,
        company_name=company_name,
        job_title=job_title,
        company_domain=company_domain,
        hunter_api_key=Config.HUNTER_API_KEY or "",
        getprospect_api_key=Config.GETPROSPECT_API_KEY or "",
        apollo_api_key=getattr(Config, "APOLLO_API_KEY", "") or "",
        snov_api_key=getattr(Config, "SNOV_API_KEY", "") or "",
    )
    if email:
        # Rough confidence bands per source, mirroring the per-service
        # scores find_recruiter_email already assigns internally.
        confidence = {"hunter": 90, "hunter_domain": 70, "getprospect": 85, "apollo": 80, "snov": 82}.get(source, 60)
        logger.info(f"Found real email for {contact_name} @ {company_name}: {email} (source={source})")
        return email, confidence

    logger.info(f"No real email found for {contact_name} @ {company_name} — leaving unset rather than guessing.")
    return None, 0
