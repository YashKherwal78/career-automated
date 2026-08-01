"""
Recruiter email finder with cascading fallback strategy:

  1. Regex extraction from JD text (always first, always free)
  2. Hunter.io Email Finder API  (50 free credits/month)
  3. GetProspect Email Finder API (50 free credits/month, fallback)

All functions return (email: str | None, source: str) so callers know
where the email came from for logging / debugging.
"""

import logging
import os
import re

import requests

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_GENERIC_PREFIXES = {
    "hr", "info", "careers", "jobs", "support",
    "contact", "apply", "talent", "hello", "admin", "team",
}

def _extract_domain_from_url(url: str) -> str | None:
    """Pull just the domain (e.g. 'meta.com') from a full URL."""
    if not url:
        return None
    try:
        # Strip scheme
        cleaned = re.sub(r"^https?://", "", url.strip()).lstrip("www.")
        return cleaned.split("/")[0]
    except Exception:
        return None


def _split_name(full_name: str) -> tuple[str, str]:
    """Split a full name into (first, last). Returns ('', '') if unparseable."""
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[0], parts[-1]
    elif len(parts) == 1:
        return parts[0], ""
    return "", ""


def _pick_best_email(emails: list[str]) -> str | None:
    """Return personal email over generic one, or None if empty list."""
    if not emails:
        return None
    personal = [e for e in emails if not any(p in e.split("@")[0] for p in _GENERIC_PREFIXES)]
    return personal[0] if personal else emails[0]


# ── Step 1: Regex from JD text ─────────────────────────────────────────────────

def extract_email_from_text(text: str) -> tuple[str | None, str]:
    """
    Extract the best email from raw text (JD, additional context, etc.).
    Returns (email, 'jd_text') or (None, 'jd_text').
    """
    if not text:
        return None, "jd_text"

    raw_matches = _EMAIL_PATTERN.findall(text)
    cleaned = []
    seen: set[str] = set()
    for m in raw_matches:
        c = m.rstrip(".,;:)'\"").lower()
        if c not in seen:
            seen.add(c)
            cleaned.append(c)

    email = _pick_best_email(cleaned)
    if email:
        logger.info(f"[EmailFinder] Found email in JD text: {email}")
    return email, "jd_text"


# ── Step 2: Hunter.io ──────────────────────────────────────────────────────────

_HUNTER_BASE = "https://api.hunter.io/v2"

def _hunter_credits_exhausted(response_json: dict) -> bool:
    """Return True when Hunter returns a quota-exceeded error."""
    errors = response_json.get("errors", [])
    for err in errors:
        code = str(err.get("code", ""))
        eid = str(err.get("id", ""))
        if code in ("429", "403") or "usage" in eid.lower() or "quota" in eid.lower():
            return True
    return False


def find_email_hunter(
    full_name: str,
    company_domain: str,
    api_key: str,
) -> tuple[str | None, str]:
    """
    Call Hunter.io Email Finder API.
    Returns (email, 'hunter') or (None, 'hunter').
    Raises RuntimeError with 'credits_exhausted' message when quota is hit.
    """
    if not api_key or not full_name or not company_domain:
        return None, "hunter"

    first, last = _split_name(full_name)
    if not first:
        return None, "hunter"

    params = {
        "domain": company_domain,
        "first_name": first,
        "last_name": last,
        "api_key": api_key,
    }

    try:
        resp = requests.get(f"{_HUNTER_BASE}/email-finder", params=params, timeout=10)
        data = resp.json()

        if not resp.ok:
            if _hunter_credits_exhausted(data):
                logger.warning("[EmailFinder] Hunter.io credits exhausted — will fallback.")
                raise RuntimeError("credits_exhausted")
            logger.warning(f"[EmailFinder] Hunter.io error: {data}")
            return None, "hunter"

        email = data.get("data", {}).get("email")
        score = data.get("data", {}).get("score", 0)

        if email and score >= 50:          # only trust if ≥50% confidence
            logger.info(f"[EmailFinder] Hunter.io found: {email} (score={score})")
            return email.lower(), "hunter"
        elif email:
            logger.info(f"[EmailFinder] Hunter.io low confidence ({score}), skipping.")

    except RuntimeError:
        raise
    except Exception as exc:
        logger.error(f"[EmailFinder] Hunter.io exception: {exc}")

    return None, "hunter"


# ── Step 2b: Hunter.io Domain Search ──────────────────────────────────────────

# Priority order for picking the best contact from domain search results
_HR_DEPARTMENTS = {"hr", "human resources", "recruiting", "talent", "people"}
_GOOD_DEPARTMENTS = {"executive", "management", "operations"}

def _score_hunter_contact(contact: dict) -> int:
    """Score a Hunter domain-search contact for recruiter relevance.
    Higher = better.
    """
    score = 0
    dept = (contact.get("department") or "").lower()
    position = (contact.get("position_raw") or contact.get("position") or "").lower()
    email_type = contact.get("type", "personal")
    confidence = contact.get("confidence", 0)

    # Skip generic emails (support@, info@)
    if email_type == "generic":
        return -100

    # Department-based scoring
    if dept in _HR_DEPARTMENTS:
        score += 100
    elif dept in _GOOD_DEPARTMENTS:
        score += 50

    # Position-based scoring
    hr_keywords = {"hr", "human resource", "recruit", "talent", "hiring", "people"}
    if any(kw in position for kw in hr_keywords):
        score += 80

    # Confidence boost
    score += confidence

    return score


def find_email_hunter_domain(
    company_domain: str,
    api_key: str,
) -> tuple[str | None, str, list[dict]]:
    """
    Call Hunter.io Domain Search API to find the best HR/recruiter email
    at a given company domain. Does NOT require a person name.

    Returns (best_email, 'hunter_domain', all_contacts).
    all_contacts is a list of dicts: [{"email": ..., "name": ..., "position": ...}, ...]
    Raises RuntimeError with 'credits_exhausted' message when quota is hit.
    """
    if not api_key or not company_domain:
        return None, "hunter_domain", []

    params = {
        "domain": company_domain,
        "api_key": api_key,
    }

    try:
        resp = requests.get(f"{_HUNTER_BASE}/domain-search", params=params, timeout=10)
        data = resp.json()

        if not resp.ok:
            if _hunter_credits_exhausted(data):
                logger.warning("[EmailFinder] Hunter.io domain-search credits exhausted.")
                raise RuntimeError("credits_exhausted")
            logger.warning(f"[EmailFinder] Hunter.io domain-search error: {data}")
            return None, "hunter_domain", []

        emails_list = data.get("data", {}).get("emails", [])
        if not emails_list:
            logger.info(f"[EmailFinder] Hunter.io domain-search: no emails found for {company_domain}")
            return None, "hunter_domain", []

        # Score and sort contacts — pick the best one (HR > executive > other)
        scored = [(e, _score_hunter_contact(e)) for e in emails_list]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Build all_contacts list (excluding generic emails)
        all_contacts = []
        for contact, score in scored:
            if score <= -100:  # skip generics
                continue
            c_email = contact.get("value")
            first = contact.get("first_name") or ""
            last = contact.get("last_name") or ""
            name = f"{first} {last}".strip()
            position = contact.get("position_raw") or contact.get("position") or ""
            dept = contact.get("department") or ""
            confidence = contact.get("confidence", 0)
            if c_email:
                all_contacts.append({
                    "email": c_email.lower(),
                    "name": name,
                    "position": position,
                    "department": dept,
                    "confidence": confidence,
                    "source": "hunter_domain",
                })

        best = all_contacts[0] if all_contacts else None
        if best:
            logger.info(
                f"[EmailFinder] Hunter.io domain-search found {len(all_contacts)} contacts. "
                f"Best: {best['email']} ({best['position']}, {best['department']}, conf={best['confidence']})"
            )
            return best["email"], "hunter_domain", all_contacts

    except RuntimeError:
        raise
    except Exception as exc:
        logger.error(f"[EmailFinder] Hunter.io domain-search exception: {exc}")

    return None, "hunter_domain", []


# ── Step 3: GetProspect ────────────────────────────────────────────────────────

_GETPROSPECT_BASE = "https://api.getprospect.com/api/v1"

def _getprospect_credits_exhausted(response_json: dict) -> bool:
    """Return True when GetProspect signals quota exceeded."""
    # GetProspect typically returns status/message fields
    msg = str(response_json.get("message", "")).lower()
    status = str(response_json.get("status", "")).lower()
    return "limit" in msg or "quota" in msg or "credits" in msg or status in ("402", "429")


def find_email_getprospect(
    full_name: str,
    company_domain: str,
    api_key: str,
) -> tuple[str | None, str]:
    """
    Call GetProspect Email Finder API.
    Returns (email, 'getprospect') or (None, 'getprospect').
    Raises RuntimeError with 'credits_exhausted' if quota is hit.
    """
    if not api_key or not full_name or not company_domain:
        return None, "getprospect"

    first, last = _split_name(full_name)
    if not first:
        return None, "getprospect"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "firstName": first,
        "lastName": last,
        "domain": company_domain,
    }

    try:
        resp = requests.post(
            f"{_GETPROSPECT_BASE}/email-finder",
            headers=headers,
            json=payload,
            timeout=10,
        )
        data = resp.json()

        if not resp.ok:
            if resp.status_code in (402, 429) or _getprospect_credits_exhausted(data):
                logger.warning("[EmailFinder] GetProspect credits exhausted.")
                raise RuntimeError("credits_exhausted")
            logger.warning(f"[EmailFinder] GetProspect error {resp.status_code}: {data}")
            return None, "getprospect"

        # GetProspect returns { "email": "...", "emailStatus": "verified"|"likely"|... }
        email = data.get("email")
        status = data.get("emailStatus", "")

        if email and status in ("verified", "likely"):
            logger.info(f"[EmailFinder] GetProspect found: {email} (status={status})")
            return email.lower(), "getprospect"
        elif email:
            logger.info(f"[EmailFinder] GetProspect uncertain status '{status}', skipping.")

    except RuntimeError:
        raise
    except Exception as exc:
        logger.error(f"[EmailFinder] GetProspect exception: {exc}")

    return None, "getprospect"





_SERVICE_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".email_finder_state")
_SERVICES = ["hunter", "getprospect"]  # rotation order

def _get_next_service() -> str:
    """Read the last-used service and return the next one in rotation."""
    try:
        if os.path.exists(_SERVICE_STATE_FILE):
            with open(_SERVICE_STATE_FILE) as f:
                last = f.read().strip()
            if last in _SERVICES:
                idx = (_SERVICES.index(last) + 1) % len(_SERVICES)
                return _SERVICES[idx]
    except Exception:
        pass
    return _SERVICES[0]  # default: start with hunter

def _save_used_service(service: str) -> None:
    """Persist which service was just used."""
    try:
        with open(_SERVICE_STATE_FILE, "w") as f:
            f.write(service)
        logger.info(f"[EmailFinder] Saved last-used service: {service}")
    except Exception as e:
        logger.error(f"[EmailFinder] Could not save service state: {e}")


# ── Master Cascading Function ──────────────────────────────────────────────────

def find_recruiter_email(
    *,
    jd_text: str = "",
    additional_context: str = "",
    recruiter_name: str = "",
    company_website: str = "",
    company_domain: str = "",
    hunter_api_key: str = "",
    getprospect_api_key: str = "",
    progress_log: list | None = None,
) -> tuple[str | None, str, list[dict]]:
    """
    Find recruiter email using a cascading strategy with round-robin service rotation.

    Args:
        progress_log: If provided, appends (icon, message) tuples for UI display.

    Returns:
        (best_email, source, all_contacts)
    """
    def _log(icon: str, msg: str):
        logger.info(f"[EmailFinder] {msg}")
        if progress_log is not None:
            progress_log.append((icon, msg))

    all_contacts: list[dict] = []

    # ── Step 1: JD / context text ──────────────────────────────────────────
    _log("📄", "Step 1: Scanning JD text for email addresses...")
    combined_text = f"{jd_text}\n{additional_context}"
    email, source = extract_email_from_text(combined_text)
    if email:
        _log("✅", f"Found email in JD text: {email}")
        return email, source, [{"email": email, "name": recruiter_name or "", "position": "", "department": "", "confidence": 100, "source": "jd_text"}]
    _log("⚪", "No email found in JD text")

    # ── Resolve domain for API calls ───────────────────────────────────────
    domain = company_domain or _extract_domain_from_url(company_website) or ""
    if domain:
        _log("🌐", f"Company domain: {domain}")
    else:
        _log("⚠️", "No company domain available — API lookups will be skipped")

    # ── Determine service order via round-robin ────────────────────────────
    first_service = _get_next_service()
    _save_used_service(first_service)

    if first_service == "hunter":
        service_order = ["hunter", "getprospect"]
    else:
        service_order = ["getprospect", "hunter"]
    _log("🔄", f"Service rotation: {' → '.join(s.title() for s in service_order)}")

    for svc in service_order:
        if svc == "hunter":
            # ── Hunter.io Person Lookup ────────────────────────────────
            if hunter_api_key and recruiter_name and domain:
                _log("🎯", f"Trying Hunter.io Person Lookup for '{recruiter_name}' @ {domain}...")
                try:
                    email, source = find_email_hunter(recruiter_name, domain, hunter_api_key)
                    if email:
                        _log("✅", f"Hunter Person Lookup found: {email}")
                        contact = {"email": email, "name": recruiter_name, "position": "", "department": "", "confidence": 90, "source": "hunter"}
                        all_contacts.append(contact)
                        return email, source, all_contacts
                    else:
                        _log("⚪", "Hunter Person Lookup: no result")
                except RuntimeError as e:
                    if "credits_exhausted" in str(e):
                        _log("🔴", "Hunter Person Lookup: credits exhausted!")
                    else:
                        _log("❌", f"Hunter Person Lookup error: {e}")
            elif not hunter_api_key:
                _log("⏭️", "Skipping Hunter Person Lookup — no API key configured")
            elif not recruiter_name:
                _log("⏭️", "Skipping Hunter Person Lookup — no recruiter name in JD")
            elif not domain:
                _log("⏭️", "Skipping Hunter Person Lookup — no domain available")

            # ── Hunter.io Domain Search ────────────────────────────────
            if hunter_api_key and domain:
                _log("🏢", f"Trying Hunter.io Domain Search for {domain}...")
                try:
                    email, source, domain_contacts = find_email_hunter_domain(domain, hunter_api_key)
                    all_contacts.extend(domain_contacts)
                    if email:
                        _log("✅", f"Hunter Domain Search found {len(domain_contacts)} contacts (best: {email})")
                    else:
                        _log("⚪", "Hunter Domain Search: no contacts found")
                except RuntimeError as e:
                    if "credits_exhausted" in str(e):
                        _log("🔴", "Hunter Domain Search: credits exhausted!")
                    else:
                        _log("❌", f"Hunter Domain Search error: {e}")

        elif svc == "getprospect":
            # ── GetProspect Person Lookup ──────────────────────────────
            if getprospect_api_key and recruiter_name and domain:
                _log("🔍", f"Trying GetProspect for '{recruiter_name}' @ {domain}...")
                try:
                    gp_email, gp_source = find_email_getprospect(recruiter_name, domain, getprospect_api_key)
                    if gp_email:
                        _log("✅", f"GetProspect found: {gp_email}")
                        contact = {"email": gp_email, "name": recruiter_name, "position": "", "department": "", "confidence": 85, "source": "getprospect"}
                        existing_emails = {c["email"] for c in all_contacts}
                        if gp_email not in existing_emails:
                            all_contacts.insert(0, contact)
                        return gp_email, gp_source, all_contacts
                    else:
                        _log("⚪", "GetProspect: no result")
                except RuntimeError as e:
                    if "credits_exhausted" in str(e):
                        _log("🔴", "GetProspect: credits exhausted!")
                    else:
                        _log("❌", f"GetProspect error: {e}")
            elif not getprospect_api_key:
                _log("⏭️", "Skipping GetProspect — no API key configured")
            elif not recruiter_name:
                _log("⏭️", "Skipping GetProspect — no recruiter name in JD")
            elif not domain:
                _log("⏭️", "Skipping GetProspect — no domain available")

    if not domain:
        _log("⚠️", "No domain available — could not run any API lookups")

    if all_contacts:
        best = all_contacts[0]
        _log("📋", f"No exact recruiter match. Returning {len(all_contacts)} company contacts (best: {best['email']})")
        return best["email"], "hunter_domain", all_contacts

    _log("❌", "All services exhausted — no email found")
    return None, "not_found", []


