import json
import sqlite3
import time
import hashlib
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from src.discovery.pipeline.ats_registry import ATSRegistry
from src.discovery.pipeline.fallback_models import VerificationResult

logger = logging.getLogger("FastPathRegistry")

SUPPORTED_ATS = {
    "greenhouse": "GreenhouseDiscoveryPlugin",
    "lever": "LeverDiscoveryPlugin",
    "ashby": "AshbyDiscoveryPlugin",
    "workday": "WorkdayDiscoveryPlugin",
    "smartrecruiters": "SmartRecruitersDiscoveryPlugin"
}

class FastPathRegistry:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.registry = ATSRegistry(db_path)

    def fast_path_company(self, company_id: str, canonical_name: str, domain: str, website: str, metadata: Dict[str, Any]) -> bool:
        """
        Attempts to register a company directly as ACTIVE in the ats_registry using trusted metadata.
        Returns True if successfully fast-pathed, False otherwise (indicating fallback is needed).
        """
        known_ats = metadata.get("known_ats")
        ats_slug = metadata.get("ats_slug")
        board_url = metadata.get("board_url")

        if not known_ats or known_ats.lower() not in SUPPORTED_ATS:
            logger.debug(f"Fast-path skipped for {company_id}: Unknown or unsupported ATS '{known_ats}'")
            return False

        known_ats = known_ats.lower()
        if not ats_slug or not board_url:
            logger.debug(f"Fast-path skipped for {company_id}: Missing ats_slug or board_url")
            return False

        # Build endpoint and metadata based on ATS type requirements
        ats_metadata = {}
        canonical_endpoint = board_url

        if known_ats == "greenhouse":
            ats_metadata["board_token"] = ats_slug
            canonical_endpoint = f"https://boards.greenhouse.io/{ats_slug}"
        elif known_ats == "lever":
            ats_metadata["board_token"] = ats_slug
            canonical_endpoint = f"https://jobs.lever.co/{ats_slug}"
        elif known_ats == "ashby":
            ats_metadata["board_token"] = ats_slug
            canonical_endpoint = f"https://jobs.ashbyhq.com/{ats_slug}"
        elif known_ats == "workday":
            # Extract tenant & site from workday slug (pattern: tenant/site)
            parts = ats_slug.split('/')
            tenant = parts[0]
            site = parts[1] if len(parts) > 1 else "careers"
            ats_metadata["tenant"] = tenant
            ats_metadata["site"] = site
            
            # Extract cluster domain from board_url if possible, fallback to tenant.wd1.myworkdayjobs.com
            parsed_url = urlparse(board_url)
            netloc = parsed_url.netloc or f"{tenant}.wd1.myworkdayjobs.com"
            canonical_endpoint = f"https://{netloc}/{site}"
        elif known_ats == "smartrecruiters":
            ats_metadata["company_identifier"] = ats_slug
            ats_metadata["board_token"] = ats_slug
            canonical_endpoint = f"https://jobs.smartrecruiters.com/{ats_slug}"
        else:
            return False

        # Generate unique hash for the endpoint
        endpoint_hash = hashlib.sha256(canonical_endpoint.encode()).hexdigest()

        # Build VerificationResult to promote
        vr = VerificationResult(
            company_id=company_id,
            company_domain=domain,
            company_name=canonical_name,
            ats_type=known_ats,
            endpoint=board_url,
            canonical_endpoint=canonical_endpoint,
            endpoint_hash=endpoint_hash,
            status='ACTIVE',
            discovery_source="JobhiveBootstrap",
            search_provider=None,
            search_query=None,
            search_rank=None,
            identity_score=1.0,
            inspector_score=1.0,
            plugin_name=SUPPORTED_ATS[known_ats],
            plugin_version="1.0",
            ats_metadata=json.dumps(ats_metadata)
        )

        try:
            self.registry.promote_endpoint(company_id, vr)
            logger.info(f"Fast-pathed company {company_id} to active {known_ats} endpoint.")
            return True
        except Exception as e:
            logger.error(f"Failed to fast-path company {company_id} in registry: {e}")
            return False
