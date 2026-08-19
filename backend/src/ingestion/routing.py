import re
import httpx
from urllib.parse import urlparse
from typing import Optional, Tuple

from src.system.logger import setup_logger
from src.discovery.ats_detector import DetectorRegistry, GoogleFormsSignature
from src.ingestion.endpoint_verification import is_endpoint_verified

logger = setup_logger("routing")

_google_forms = GoogleFormsSignature()

# A bare "jobs@acme.com" or "mailto:jobs@acme.com" apply_link means the
# posting says "email your CV to us" instead of giving a link/form.
# Deliberately excludes "/" and ":" from the local/domain parts so a URL
# with an email-shaped query param (?ref=jobs@acme.com) never matches --
# the WHOLE apply_link has to be an email, not merely contain one.
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _is_email_address(apply_link: str) -> bool:
    candidate = apply_link[len("mailto:"):] if apply_link.lower().startswith("mailto:") else apply_link
    return bool(_EMAIL_RE.match(candidate.strip()))


def resolve_connector(apply_link: str) -> Tuple[Optional[str], str]:
    # No fetch needed -- same free short-circuit as the Google Forms check
    # below, just checking the string shape instead of a URL pattern.
    if _is_email_address(apply_link):
        return "email_apply", "email_apply"

    # GoogleFormsSignature.detect() is purely URL-pattern based (it ignores
    # the response argument entirely), so it can answer before we spend a
    # network round-trip -- and using the detector rather than an ad-hoc
    # substring copy keeps the pattern defined in exactly one place.
    if _google_forms.detect(apply_link, None):
        return _google_forms.provider_id, "google_forms"

    try:
        response = httpx.get(apply_link, timeout=10.0, follow_redirects=True)
    except Exception as e:
        logger.info(f"[routing] failed to fetch {apply_link}: {e}")
        return None, "fetch failed"

    # A URL pattern matching is not evidence the posting exists: a dead
    # greenhouse/lever link still looks exactly like a live one. Require the
    # page to actually have served content before treating the detection as
    # routable.
    if getattr(response, "status_code", None) != 200:
        logger.info(f"[routing] {apply_link} returned HTTP {getattr(response, 'status_code', '?')}")
        return None, f"apply link returned HTTP {getattr(response, 'status_code', '?')}"

    detector = DetectorRegistry.detect_all(apply_link, response)
    if not detector:
        return None, "unrecognized URL"

    company_domain = urlparse(apply_link).netloc
    connector = detector.provider_id

    if is_endpoint_verified(company_domain, connector):
        return connector, f"{connector} (verified)"

    # Deliberately NOT writing a row here. The previous implementation called
    # mark_endpoint_verified() to insert a guessed `ats_registry` row, which
    # was wrong in four separate ways: it never checked the response status
    # (404s were marked VERIFIED), it keyed on the ATS *vendor* host
    # (boards.greenhouse.io) rather than the tenant, it left company_id NULL
    # (other code joins on it) with a status value nothing else recognizes,
    # and on Postgres it would hit the ats_registry.provider_id -> ats_providers
    # foreign key for any provider outside the 8 seeded rows and crash the run.
    # Corrupting a 62k-row production table is a far worse outcome than a lead
    # landing in the human review queue, so an unverified endpoint is simply
    # unroutable. Tenant-keyed, FK-safe write-back verification is a follow-up.
    logger.info(f"[routing] {connector} endpoint for {company_domain} is not verified in ats_registry")
    return None, f"{connector} endpoint not verified for {company_domain}"
