"""
Encrypt/decrypt round-trip and lifecycle tests for google_session.py --
the encrypted, per-candidate Playwright storage_state store that lets
GoogleFormsAdapter reuse a live-logged-in Google session (see
google_connect.py) instead of hitting a sign-in gate on every application.

Same pattern as would apply to ats_credentials.py: monkeypatch the store
path to a tmp file and ENCRYPTION_KEY to a throwaway Fernet key, so tests
never touch the real backend/data store or depend on a real production
key being present in the environment.
"""
from cryptography.fernet import Fernet

from src.applications import google_session


def _use_tmp_store(monkeypatch, tmp_path):
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(google_session, "_STORE_PATH", str(tmp_path / "google_sessions.json"))


def test_get_session_returns_none_when_never_connected(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    assert google_session.get_session("user-1") is None
    assert google_session.has_session("user-1") is False


def test_get_session_returns_none_for_falsy_user_id(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    assert google_session.get_session(None) is None
    assert google_session.get_session("") is None


def test_save_then_get_round_trips_the_storage_state(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    state = {"cookies": [{"name": "SID", "value": "abc123", "domain": ".google.com"}], "origins": []}

    google_session.save_session("user-1", state)

    assert google_session.has_session("user-1") is True
    assert google_session.get_session("user-1") == state


def test_the_stored_blob_is_actually_encrypted_on_disk(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    state = {"cookies": [{"name": "SID", "value": "super-secret-session-value"}], "origins": []}

    google_session.save_session("user-1", state)

    raw = (tmp_path / "google_sessions.json").read_text()
    assert "super-secret-session-value" not in raw


def test_save_overwrites_a_previous_session_for_the_same_user(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    google_session.save_session("user-1", {"cookies": [{"name": "old"}], "origins": []})
    google_session.save_session("user-1", {"cookies": [{"name": "new"}], "origins": []})

    assert google_session.get_session("user-1")["cookies"] == [{"name": "new"}]


def test_sessions_are_isolated_per_user(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    google_session.save_session("user-1", {"cookies": [{"name": "one"}], "origins": []})
    google_session.save_session("user-2", {"cookies": [{"name": "two"}], "origins": []})

    assert google_session.get_session("user-1")["cookies"] == [{"name": "one"}]
    assert google_session.get_session("user-2")["cookies"] == [{"name": "two"}]


def test_delete_session_removes_it(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    google_session.save_session("user-1", {"cookies": [], "origins": []})
    assert google_session.has_session("user-1") is True

    google_session.delete_session("user-1")

    assert google_session.has_session("user-1") is False
    assert google_session.get_session("user-1") is None


def test_delete_session_is_a_noop_when_nothing_was_stored(monkeypatch, tmp_path):
    _use_tmp_store(monkeypatch, tmp_path)
    # Must not raise even though "ghost" was never saved.
    google_session.delete_session("ghost")
    assert google_session.has_session("ghost") is False
