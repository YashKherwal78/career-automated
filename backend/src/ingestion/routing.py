import httpx
from urllib.parse import urlparse
from typing import Optional, Tuple

from src.system.logger import setup_logger
from src.discovery.ats_detector import DetectorRegistry, GoogleFormsSignature
from src.ingestion.endpoint_verification import is_endpoint_verified, mark_endpoint_verified

logger = setup_logger("routing")

_google_forms = GoogleFormsSignature()


def resolve_connector(apply_link: str) -> Tuple[Optional[str], str]:
    if "forms.gle/" in apply_link or "docs.google.com/forms/" in apply_link:
        return "google_forms", "google_forms"

    try:
        response = httpx.get(apply_link, timeout=10.0, follow_redirects=True)
    except Exception as e:
        logger.info(f"[routing] failed to fetch {apply_link}: {e}")
        return None, "fetch failed"

    detector = DetectorRegistry.detect_all(apply_link, response)
    if not detector:
        return None, "unrecognized URL"

    company_domain = urlparse(apply_link).netloc
    connector = detector.provider_id

    if is_endpoint_verified(company_domain, connector):
        return connector, f"{connector} (verified)"

    mark_endpoint_verified(company_domain, connector, apply_link)
    return connector, f"{connector} (newly verified)"
