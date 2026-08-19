"""
Per-candidate persisted Google web session, used to submit Google Forms
that gate on "Sign in to continue" -- something an OAuth access token
can't do (Google doesn't expose an API to mint a signed-in web session
from a token; the only way to get one is a real login inside a real
browser). See google_connect.py for how this gets populated: a live,
human-driven login (same captcha_bridge screenshot/click/type relay used
for CAPTCHAs) captures the resulting Playwright `storage_state()` once,
so future Google Forms applications can reuse it instead of asking the
candidate to log in every single time.

Same storage shape and encryption as ats_credentials.py (Fernet, keyed
off ENCRYPTION_KEY), but keyed by candidate user_id instead of
platform:tenant, and storing a session blob instead of a password.
Meaningfully more sensitive than an ATS tenant password: this is a live,
authenticated Google session, not a synthetic per-tenant login -- treat
the store and ENCRYPTION_KEY with the same care as any other credential
material.
"""
import json
import os
from typing import Optional

from src.applications.profile import CryptoManager

_STORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "google_sessions.json"
)


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


def save_session(user_id: str, storage_state: dict):
    """Encrypts and persists a Playwright storage_state() dict for this
    candidate, overwriting any previous session (a fresh connect always
    supersedes the old one)."""
    store = _load_store()
    crypto = CryptoManager()
    store[user_id] = {"storage_state_encrypted": crypto.encrypt(json.dumps(storage_state))}
    _save_store(store)


def get_session(user_id: Optional[str]) -> Optional[dict]:
    """Returns the decrypted storage_state dict for this candidate, or
    None if they've never connected (or user_id itself is falsy -- lets
    call sites pass an optional/absent user_id without a guard)."""
    if not user_id:
        return None
    store = _load_store()
    entry = store.get(user_id)
    if not entry:
        return None
    crypto = CryptoManager()
    try:
        return json.loads(crypto.decrypt(entry["storage_state_encrypted"]))
    except Exception:
        return None


def has_session(user_id: str) -> bool:
    return user_id in _load_store()


def delete_session(user_id: str):
    """Removes a candidate's saved session -- called both on explicit
    "Disconnect" and when an apply run finds the saved session no longer
    signs the candidate in (expired/invalidated), so Settings correctly
    shows "not connected" instead of a session that silently stopped
    working."""
    store = _load_store()
    if user_id in store:
        del store[user_id]
        _save_store(store)
