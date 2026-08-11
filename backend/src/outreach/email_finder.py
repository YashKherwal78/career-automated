"""
Recruiter/HR email finder with cascading fallback strategy:

  1. Regex extraction from JD text (always first, always free)
  2. Hunter.io Email Finder / Domain Search API
  3. GetProspect Email Finder API
  4. Apollo API
  5. Snov.io API
  6. DuckDuckGo company-domain inference (when no company website is known)

All lookup functions return (email, source) or (email, source, contacts) so
callers know where the email came from. This replaces the previous
`EnrichmentLayer.find_contacts`/`fallback_duckduckgo_search`, which returned
hardcoded mock data and an unimplemented stub respectively — this module
does real API calls and real DuckDuckGo search.
"""
from __future__ import annotations
import re
from src.system.logger import setup_logger

logger = setup_logger('email_finder')
import requests

_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_GENERIC_PREFIXES = {
    "hr", "info", "careers", "jobs", "support",
    "contact", "apply", "talent", "hello", "admin", "team",
}


def _extract_domain_from_url(url: str) -> str:
    if not url:
        return ""
    try:
        cleaned = re.sub(r"^https?://", "", url.strip()).lstrip("www.")
        return cleaned.split("/")[0]
    except Exception:
        return ""


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split()
    if len(parts) >= 2:
        return parts[0], parts[-1]
    elif len(parts) == 1:
        return parts[0], ""
    return "", ""


def _pick_best_email(emails: list) -> str:
    if not emails:
        return ""
    personal = [e for e in emails if not any(p in e.split("@")[0] for p in _GENERIC_PREFIXES)]
    return personal[0] if personal else emails[0]


# ── Step 1: Regex from JD text ──────────────────────────────────────────

def extract_email_from_text(text: str) -> tuple:
    if not text:
        return "", "jd_text"
    raw_matches = _EMAIL_PATTERN.findall(text)
    cleaned, seen = [], set()
    for m in raw_matches:
        c = m.rstrip(".,;:)'\"").lower()
        if c not in seen:
            seen.add(c)
            cleaned.append(c)
    email = _pick_best_email(cleaned)
    if email:
        logger.info(f"Found email in JD text: {email}")
    return email, "jd_text"


# ── Step 2: Hunter.io ────────────────────────────────────────────────────

_HUNTER_BASE = "https://api.hunter.io/v2"


def _hunter_credits_exhausted(response_json: dict) -> bool:
    for err in response_json.get("errors", []):
        code = str(err.get("code", ""))
        eid = str(err.get("id", ""))
        if code in ("429", "403") or "usage" in eid.lower() or "quota" in eid.lower():
            return True
    return False


def find_email_hunter(full_name: str, company_domain: str, api_key: str) -> tuple:
    if not api_key or not full_name or not company_domain:
        return "", "hunter"
    first, last = _split_name(full_name)
    if not first:
        return "", "hunter"
    params = {"domain": company_domain, "first_name": first, "last_name": last, "api_key": api_key}
    try:
        resp = requests.get(f"{_HUNTER_BASE}/email-finder", params=params, timeout=10)
        data = resp.json()
        if not resp.ok:
            if _hunter_credits_exhausted(data):
                raise RuntimeError("credits_exhausted")
            logger.info(f"Hunter.io error: {data}")
            return "", "hunter"
        email = data.get("data", {}).get("email")
        score = data.get("data", {}).get("score", 0)
        if email and score >= 50:
            logger.info(f"Hunter.io found: {email} (score={score})")
            return email.lower(), "hunter"
    except RuntimeError:
        raise
    except Exception as exc:
        logger.info(f"Hunter.io exception: {exc}")
    return "", "hunter"


_HR_DEPARTMENTS = {"hr", "human resources", "recruiting", "talent", "people"}
_GOOD_DEPARTMENTS = {"executive", "management", "operations"}


def _score_hunter_contact(contact: dict) -> int:
    score = 0
    dept = (contact.get("department") or "").lower()
    position = (contact.get("position_raw") or contact.get("position") or "").lower()
    if contact.get("type", "personal") == "generic":
        return -100
    if dept in _HR_DEPARTMENTS:
        score += 100
    elif dept in _GOOD_DEPARTMENTS:
        score += 50
    if any(kw in position for kw in {"hr", "human resource", "recruit", "talent", "hiring", "people"}):
        score += 80
    score += contact.get("confidence", 0)
    return score


def find_email_hunter_domain(company_domain: str, api_key: str) -> tuple:
    """Domain-wide search for the best HR/recruiter email — doesn't need a name."""
    if not api_key or not company_domain:
        return "", "hunter_domain", []
    try:
        resp = requests.get(f"{_HUNTER_BASE}/domain-search",
                             params={"domain": company_domain, "api_key": api_key, "department": "hr"}, timeout=10)
        data = resp.json()
        if not resp.ok and _hunter_credits_exhausted(data):
            raise RuntimeError("credits_exhausted")
        emails_list = data.get("data", {}).get("emails", [])
        if not emails_list:
            resp = requests.get(f"{_HUNTER_BASE}/domain-search",
                                 params={"domain": company_domain, "api_key": api_key}, timeout=10)
            data = resp.json()
            emails_list = data.get("data", {}).get("emails", [])
        if not emails_list:
            return "", "hunter_domain", []

        scored = sorted(((e, _score_hunter_contact(e)) for e in emails_list), key=lambda x: x[1], reverse=True)
        all_contacts = []
        for contact, score in scored:
            if score <= -100:
                continue
            c_email = contact.get("value")
            if not c_email:
                continue
            name = f"{contact.get('first_name') or ''} {contact.get('last_name') or ''}".strip()
            all_contacts.append({
                "email": c_email.lower(), "name": name,
                "position": contact.get("position_raw") or contact.get("position") or "",
                "department": contact.get("department") or "",
                "confidence": contact.get("confidence", 0), "source": "hunter_domain",
            })
        if all_contacts:
            best = all_contacts[0]
            logger.info(f"Hunter.io domain-search found {len(all_contacts)} contacts, best: {best['email']}")
            return best["email"], "hunter_domain", all_contacts
    except RuntimeError:
        raise
    except Exception as exc:
        logger.info(f"Hunter.io domain-search exception: {exc}")
    return "", "hunter_domain", []


# ── Step 3: GetProspect ──────────────────────────────────────────────────

_GETPROSPECT_BASE = "https://api.getprospect.com/public/v1"


def find_email_getprospect(full_name: str, company_domain: str, api_key: str) -> tuple:
    if not api_key or not full_name or not company_domain:
        return "", "getprospect"
    first, last = _split_name(full_name)
    if not first:
        return "", "getprospect"
    try:
        resp = requests.post(f"{_GETPROSPECT_BASE}/emails/search",
                              headers={"Content-Type": "application/json", "apiKey": api_key},
                              json={"firstName": first, "lastName": last, "domain": company_domain}, timeout=10)
        data = resp.json()
        if not resp.ok:
            msg, status = str(data.get("message", "")).lower(), str(data.get("status", "")).lower()
            if resp.status_code in (402, 429) or "limit" in msg or "quota" in msg or "credits" in msg:
                raise RuntimeError("credits_exhausted")
            return "", "getprospect"
        email = data.get("email")
        if email and data.get("emailStatus", "") in ("verified", "likely"):
            logger.info(f"GetProspect found: {email}")
            return email.lower(), "getprospect"
    except RuntimeError:
        raise
    except Exception as exc:
        logger.info(f"GetProspect exception: {exc}")
    return "", "getprospect"


# ── Step 4: Apollo ───────────────────────────────────────────────────────

_APOLLO_BASE = "https://api.apollo.io/v1"


def find_email_apollo(full_name: str, company_domain: str, api_key: str) -> tuple:
    if not api_key or not full_name or not company_domain:
        return "", "apollo"
    first, last = _split_name(full_name)
    if not first:
        return "", "apollo"
    try:
        resp = requests.post(f"{_APOLLO_BASE}/people/match",
                              json={"api_key": api_key, "first_name": first, "last_name": last, "domain": company_domain},
                              timeout=10)
        data = resp.json()
        if not resp.ok:
            if resp.status_code in (402, 429):
                raise RuntimeError("credits_exhausted")
            return "", "apollo"
        email = data.get("person", {}).get("email")
        if email:
            logger.info(f"Apollo found: {email}")
            return email.lower(), "apollo"
    except RuntimeError:
        raise
    except Exception as exc:
        logger.info(f"Apollo exception: {exc}")
    return "", "apollo"


# ── Step 5: Snov.io ──────────────────────────────────────────────────────

_SNOV_BASE = "https://api.snov.io/v1"


def find_email_snov(full_name: str, company_domain: str, api_credentials: str) -> tuple:
    """api_credentials is 'client_id:client_secret'."""
    if not api_credentials or not full_name or not company_domain:
        return "", "snov"
    parts = api_credentials.split(":")
    if len(parts) != 2:
        return "", "snov"
    client_id, client_secret = parts
    first, last = _split_name(full_name)
    if not first:
        return "", "snov"
    try:
        token_resp = requests.post(f"{_SNOV_BASE}/oauth/access_token", data={
            "grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret,
        }, timeout=10)
        if not token_resp.ok:
            return "", "snov"
        access_token = token_resp.json().get("access_token")
        if not access_token:
            return "", "snov"
        resp = requests.post(f"{_SNOV_BASE}/get-emails-from-names",
                              headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                              json={"firstName": first, "lastName": last, "domain": company_domain}, timeout=15)
        data = resp.json()
        if not resp.ok:
            if resp.status_code in (402, 429):
                raise RuntimeError("credits_exhausted")
            return "", "snov"
        data_list = data.get("data", [])
        if data_list:
            for e in data_list[0].get("emails", []):
                if e.get("email"):
                    logger.info(f"Snov.io found: {e['email']}")
                    return str(e["email"]).lower(), "snov"
    except RuntimeError:
        raise
    except Exception as exc:
        logger.info(f"Snov.io exception: {exc}")
    return "", "snov"


# ── Company-domain inference via DuckDuckGo ─────────────────────────────

def search_company_domain(company_name: str, context: str = "") -> str:
    """Infer a company's official domain via DuckDuckGo when no website is
    already known — replaces the previous unimplemented DuckDuckGo stub."""
    if not company_name:
        return ""
    try:
        from ddgs import DDGS
        query = f'"{company_name}" official website'
        if context:
            query = f'"{company_name}" {context} official website'
        results = DDGS().text(query, max_results=5)
        if not results:
            return ""
        skip_domains = {
            "linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com",
            "youtube.com", "github.com", "wikipedia.org", "glassdoor.com", "indeed.com",
            "naukri.com", "ambitionbox.com", "crunchbase.com", "zoominfo.com",
            "google.com", "bing.com", "trustpilot.com", "capterra.com", "g2.com",
        }
        # DuckDuckGo search ranking is not reliable enough to trust blindly
        # — confirmed live: a query for "Zomato" surfaced an unrelated
        # interview-prep site (prepfully.com) ahead of zomato.com. Using a
        # wrong domain here doesn't just fail safely — it feeds a WRONG
        # but real company's domain into Hunter/GetProspect, which then
        # return a real person's real email at the WRONG company,
        # actively worse than finding nothing. Require the company name
        # to actually appear in the candidate domain (normalized,
        # alphanumeric-only comparison) before trusting it; if no result
        # passes that bar, return not-found rather than guess.
        normalized_name = re.sub(r"[^a-z0-9]", "", company_name.lower())
        candidates = []
        for r in results:
            href = r.get("href", "") or r.get("url", "")
            if not href:
                continue
            domain = _extract_domain_from_url(href)
            # Only skip a domain for being a search-engine/social/job-board
            # host if it ISN'T what we're actually looking for — confirmed
            # live: researching "Google" itself could never resolve
            # because google.com is (rightly) in the skip list for
            # filtering search-engine noise out of OTHER companies'
            # results, but that same list was blocking Google from ever
            # matching as the target company.
            is_skipped = any(domain == skip or domain.endswith("." + skip) for skip in skip_domains)
            if is_skipped and normalized_name not in re.split(r"[.\-]", domain.lower()):
                continue
            if not domain or "." not in domain:
                continue
            candidates.append(domain)

        # Two-tier match, strongest signal first. A loose "name appears
        # anywhere in the domain" check has its own false-positive risk —
        # confirmed live: for "Zomato" it matched
        # "zomatoproject2.azurewebsites.net", someone's unrelated clone
        # project, not the real zomato.com. Prefer an exact match on the
        # domain's OWN registrable label first (e.g. "burberry" ==
        # "burberry" for burberryplc.com's root, "brita" == "brita" for
        # brita.in); only fall back to the looser subdomain-inclusive
        # substring check (needed for genuine cases like
        # "in.burberry.com", where the company label isn't the first one)
        # if no exact match exists.
        exact_matches = []
        for domain in candidates:
            labels = re.split(r"[.\-]", domain.lower())
            root_labels = [re.sub(r"[^a-z0-9]", "", l) for l in labels]
            if normalized_name in root_labels:
                exact_matches.append(domain)

        if exact_matches:
            # Among exact matches, big companies' own careers/product
            # subdomains routinely outrank their plain corporate domain in
            # search results (confirmed live: "leap.microsoft.com",
            # "aws.amazon.com", "careers.swiggy.com" all beat the bare
            # root domain for their respective companies) — but Hunter/
            # GetProspect/etc. index emails against the main corporate
            # domain, not a specific subdomain, so picking the subdomain
            # silently dooms the lookup to find nothing. Prefer the
            # candidate with the FEWEST dot-separated labels (i.e.
            # "paytm.com" over "careers.paytm.com"), and among ties,
            # prefer the company label appearing earliest (closest to
            # being the actual second-level domain).
            def _simplicity(domain):
                parts = domain.lower().split(".")
                stripped_parts = [re.sub(r"[^a-z0-9]", "", p) for p in parts]
                name_position = stripped_parts.index(normalized_name) if normalized_name in stripped_parts else len(stripped_parts)
                return (len(parts), name_position)

            best = min(exact_matches, key=_simplicity)
            logger.info(f"Inferred company domain for '{company_name}': {best} (exact label match, simplest of {len(exact_matches)})")
            return best

        for domain in candidates:
            domain_stripped = re.sub(r"[^a-z0-9]", "", domain.lower())
            if normalized_name and normalized_name in domain_stripped and len(domain_stripped) <= len(normalized_name) + 15:
                logger.info(f"Inferred company domain for '{company_name}': {domain} (substring match)")
                return domain

        logger.info(f"No search result's domain matched '{company_name}' closely enough — not guessing.")
        return ""
    except Exception as e:
        logger.info(f"Error searching company domain for {company_name}: {e}")
        return ""


# ── Master cascading function ───────────────────────────────────────────

_SERVICES = ["hunter", "getprospect", "apollo", "snov"]
_last_used_service = _SERVICES[1]


def _get_next_service() -> str:
    global _last_used_service
    idx = (_SERVICES.index(_last_used_service) + 1) % len(_SERVICES)
    return _SERVICES[idx]


def _save_used_service(service: str) -> None:
    global _last_used_service
    if service in _SERVICES:
        _last_used_service = service


def find_recruiter_email(
    *,
    jd_text: str = "",
    additional_context: str = "",
    recruiter_name: str = "",
    company_website: str = "",
    company_domain: str = "",
    company_name: str = "",
    job_title: str = "",
    hunter_api_key: str = "",
    getprospect_api_key: str = "",
    apollo_api_key: str = "",
    snov_api_key: str = "",
) -> tuple:
    """
    Find a real HR/recruiter email for a job posting using a cascading
    strategy: JD text -> Hunter -> GetProspect -> Apollo -> Snov.io,
    inferring the company domain via DuckDuckGo if none is already known.

    Returns (best_email, source, all_contacts) — all_contacts is a list of
    {"email", "name", "position", "department", "confidence", "source"}.
    """
    all_contacts: list = []

    email, source = extract_email_from_text(f"{jd_text}\n{additional_context}")
    if email:
        return email, source, [{"email": email, "name": recruiter_name, "position": "", "department": "",
                                 "confidence": 100, "source": "jd_text"}]

    domain = company_domain or _extract_domain_from_url(company_website) or ""
    if not domain and company_name:
        domain = search_company_domain(company_name, context=job_title)

    if not domain:
        logger.info("No company domain available — cannot run email-finder APIs.")
        return "", "not_found", []

    first_service = _get_next_service()
    _save_used_service(first_service)
    idx = _SERVICES.index(first_service)
    service_order = [_SERVICES[(idx + i) % len(_SERVICES)] for i in range(len(_SERVICES))]

    for svc in service_order:
        if svc == "hunter" and hunter_api_key:
            if recruiter_name:
                try:
                    email, source = find_email_hunter(recruiter_name, domain, hunter_api_key)
                    if email:
                        all_contacts.append({"email": email, "name": recruiter_name, "position": "",
                                              "department": "", "confidence": 90, "source": "hunter"})
                        return email, source, all_contacts
                except RuntimeError:
                    pass
            try:
                email, source, domain_contacts = find_email_hunter_domain(domain, hunter_api_key)
                all_contacts.extend(domain_contacts)
                if email:
                    return email, source, all_contacts
            except RuntimeError:
                pass

        elif svc == "getprospect" and getprospect_api_key and recruiter_name:
            try:
                email, source = find_email_getprospect(recruiter_name, domain, getprospect_api_key)
                if email:
                    contact = {"email": email, "name": recruiter_name, "position": "", "department": "",
                               "confidence": 85, "source": "getprospect"}
                    if email not in {c["email"] for c in all_contacts}:
                        all_contacts.insert(0, contact)
                    return email, source, all_contacts
            except RuntimeError:
                pass

        elif svc == "apollo" and apollo_api_key and recruiter_name:
            try:
                email, source = find_email_apollo(recruiter_name, domain, apollo_api_key)
                if email:
                    contact = {"email": email, "name": recruiter_name, "position": "", "department": "",
                               "confidence": 80, "source": "apollo"}
                    if email not in {c["email"] for c in all_contacts}:
                        all_contacts.insert(0, contact)
                    return email, source, all_contacts
            except RuntimeError:
                pass

        elif svc == "snov" and snov_api_key and recruiter_name:
            try:
                email, source = find_email_snov(recruiter_name, domain, snov_api_key)
                if email:
                    contact = {"email": email, "name": recruiter_name, "position": "", "department": "",
                               "confidence": 82, "source": "snov"}
                    if email not in {c["email"] for c in all_contacts}:
                        all_contacts.insert(0, contact)
                    return email, source, all_contacts
            except RuntimeError:
                pass

    if all_contacts:
        best = all_contacts[0]
        return best["email"], "hunter_domain", all_contacts

    return "", "not_found", []
