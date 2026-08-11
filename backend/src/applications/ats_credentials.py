"""
Per-employer credential storage for ATS platforms that require a real
account (Workday, and any future account-gated platform this project
decides to support). One entry per tenant/employer, not per job posting —
applying to five postings at the same company reuses the same account,
exactly like a real candidate would.

Passwords are never a guessable pattern (no name/DOB derivation) — each is
a fresh random string, generated once per tenant and stored encrypted via
the existing CryptoManager (Fernet, keyed off ENCRYPTION_KEY). The store
itself is a small local JSON file; encrypted password blobs are ~100-150
bytes each, so even hundreds of tenants stay well under a few hundred KB.
"""
import json
import os
import secrets
import string

from src.applications.profile import CryptoManager

_STORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "ats_credentials.json"
)


def _generate_password(length: int = 16) -> str:
    # Mixed-case letters, digits, and a couple of symbols most ATS signup
    # forms accept — random, not derived from any candidate fact. 16 chars
    # (not the original 20) — confirmed live that at least one real tenant
    # (a SuccessFactors instance) enforces an 18-character MAX, and a
    # purely random draw from a mixed alphabet isn't guaranteed to
    # actually contain an uppercase/lowercase/digit-or-symbol even though
    # it's overwhelmingly likely to at this length — several real
    # registration forms explicitly require at least one of each class,
    # so this deterministically includes one of each before filling the
    # rest randomly and shuffling, rather than leaving it to chance.
    upper, lower, digit, symbol = string.ascii_uppercase, string.ascii_lowercase, string.digits, "!@#$%^&*"
    alphabet = upper + lower + digit + symbol
    required = [secrets.choice(upper), secrets.choice(lower), secrets.choice(digit + symbol)]
    rest = [secrets.choice(alphabet) for _ in range(length - len(required))]
    chars = required + rest
    for i in range(len(chars) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        chars[i], chars[j] = chars[j], chars[i]
    return "".join(chars)


def _load_store() -> dict:
    if not os.path.exists(_STORE_PATH):
        return {}
    try:
        with open(_STORE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_store(store: dict):
    os.makedirs(os.path.dirname(_STORE_PATH), exist_ok=True)
    with open(_STORE_PATH, "w") as f:
        json.dump(store, f, indent=2)


def get_or_create_credentials(platform: str, tenant: str, email: str) -> dict:
    """Returns {"email": ..., "password": ...} for this platform+tenant,
    creating and persisting a new random password the first time this
    tenant is seen. Safe to call repeatedly — later calls return the same
    stored credentials rather than generating a new password each time."""
    store = _load_store()
    key = f"{platform}:{tenant}"
    crypto = CryptoManager()

    if key in store:
        entry = store[key]
        return {"email": entry["email"], "password": crypto.decrypt(entry["password_encrypted"])}

    password = _generate_password()
    store[key] = {"email": email, "password_encrypted": crypto.encrypt(password)}
    _save_store(store)
    return {"email": email, "password": password}


def has_credentials(platform: str, tenant: str) -> bool:
    store = _load_store()
    return f"{platform}:{tenant}" in store
