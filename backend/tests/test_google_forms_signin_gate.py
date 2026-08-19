"""
Sign-in-gate handling for GoogleFormsAdapter -- the part that makes
google_session.py/google_connect.py actually useful. A Google Form that
requires signing in redirects to accounts.google.com before any question
ever renders; GoogleFormsHandler would just find zero questions and fail
opaquely, so the adapter detects the gate itself and returns a diagnosed
REVIEW_REQUIRED instead, using whichever saved session (if any) was
passed into the browser context.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.applications.adapters.google_forms_adapter import GoogleFormsAdapter, _is_google_signin_page
from src.applications.handlers.google_forms import GoogleFormsHandler


def _job(**overrides):
    job = {
        "id": "job-1", "job_title": "Backend Engineer", "company_name": "Acme",
        "location": "Remote", "apply_url": "https://forms.gle/abc123",
        "execution_dir": "", "description": "",
    }
    job.update(overrides)
    return job


# ---------------------------------------------------------------------------
# _is_google_signin_page
# ---------------------------------------------------------------------------

def test_detects_a_redirect_to_accounts_google_com():
    page = MagicMock(url="https://accounts.google.com/ServiceLogin?service=wise", title=lambda: "Sign in")
    assert _is_google_signin_page(page) is True


def test_detects_by_title_when_url_does_not_redirect():
    page = MagicMock(url="https://docs.google.com/forms/d/e/abc/viewform", title=lambda: "Sign in - Google Accounts")
    assert _is_google_signin_page(page) is True


def test_a_normal_form_is_not_flagged():
    page = MagicMock(url="https://docs.google.com/forms/d/e/abc/viewform", title=lambda: "Backend Engineer Application")
    assert _is_google_signin_page(page) is False


def test_survives_page_reads_raising():
    page = MagicMock()
    type(page).url = property(lambda self: (_ for _ in ()).throw(RuntimeError("detached")))
    assert _is_google_signin_page(page) is False


# ---------------------------------------------------------------------------
# Adapter behavior when the gate is hit
# ---------------------------------------------------------------------------

@pytest.fixture
def gated_browser():
    """Fresh context (no saved session) that lands on the sign-in page."""
    with patch("src.applications.adapters.google_forms_adapter.LaunchedBrowser") as lb_cls:
        page = MagicMock(url="https://accounts.google.com/ServiceLogin", title=lambda: "Sign in")
        lb_cls.return_value.__enter__.return_value = MagicMock(page=page)
        yield lb_cls, page


def test_no_saved_session_returns_review_required_with_connect_copy(tmp_path, gated_browser):
    lb_cls, page = gated_browser
    with patch("src.applications.adapters.google_forms_adapter.google_session.get_session", return_value=None), \
         patch("src.applications.adapters.google_forms_adapter.google_session.delete_session") as delete_session:
        result = GoogleFormsAdapter().apply(
            {**_job(), "execution_dir": str(tmp_path)},
            resume_path="/tmp/resume.pdf", profile_manager=MagicMock(), test_mode=True, user_id="user-1",
        )

    assert result.status == "REVIEW_REQUIRED"
    assert "connect" in result.failure_reason.lower()
    assert "google" in result.failure_reason.lower()
    delete_session.assert_not_called()
    # A fresh context (no session to reuse yet) is a plain, unkeyed call.
    _, kwargs = lb_cls.call_args
    assert kwargs.get("storage_state") is None


def test_stale_saved_session_is_deleted_and_reported_as_expired(tmp_path, gated_browser):
    lb_cls, page = gated_browser
    saved = {"cookies": [{"name": "SID", "value": "stale"}], "origins": []}
    with patch("src.applications.adapters.google_forms_adapter.google_session.get_session", return_value=saved), \
         patch("src.applications.adapters.google_forms_adapter.google_session.delete_session") as delete_session:
        result = GoogleFormsAdapter().apply(
            {**_job(), "execution_dir": str(tmp_path)},
            resume_path="/tmp/resume.pdf", profile_manager=MagicMock(), test_mode=True, user_id="user-1",
        )

    assert result.status == "REVIEW_REQUIRED"
    assert "expired" in result.failure_reason.lower() or "reconnect" in result.failure_reason.lower()
    delete_session.assert_called_once_with("user-1")
    # The stale session was still the one handed to LaunchedBrowser for this attempt.
    _, kwargs = lb_cls.call_args
    assert kwargs.get("storage_state") == saved


def test_signin_gate_never_constructs_a_handler(tmp_path, gated_browser):
    """A gate hit must short-circuit before GoogleFormsHandler is built at
    all -- constructing it would immediately call _extract_questions() on a
    sign-in page and fail through an unrelated, confusing path."""
    lb_cls, page = gated_browser
    with patch("src.applications.adapters.google_forms_adapter.google_session.get_session", return_value=None), \
         patch("src.applications.adapters.google_forms_adapter.GoogleFormsHandler") as handler_cls:
        GoogleFormsAdapter().apply(
            {**_job(), "execution_dir": str(tmp_path)},
            resume_path="/tmp/resume.pdf", profile_manager=MagicMock(), test_mode=True, user_id="user-1",
        )

    handler_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Adapter behavior on a normal (non-gated) form -- confirms the saved
# session is actually threaded into LaunchedBrowser, and that a normal
# form is entirely unaffected by any of the above.
# ---------------------------------------------------------------------------

def test_a_saved_session_is_passed_to_the_browser_context(tmp_path):
    saved = {"cookies": [{"name": "SID", "value": "still-good"}], "origins": []}
    with patch("src.applications.adapters.google_forms_adapter.LaunchedBrowser") as lb_cls:
        page = MagicMock(url="https://docs.google.com/forms/d/e/abc/viewform", title=lambda: "Backend Engineer Application")
        lb_cls.return_value.__enter__.return_value = MagicMock(page=page)

        with patch("src.applications.adapters.google_forms_adapter.google_session.get_session", return_value=saved), \
             patch.object(GoogleFormsHandler, "execute", lambda self: {"status": "COMPLETED", "telemetry": {}}), \
             patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search", side_effect=lambda lead: lead):
            result = GoogleFormsAdapter().apply(
                {**_job(), "execution_dir": str(tmp_path)},
                resume_path="/tmp/resume.pdf", profile_manager=MagicMock(), test_mode=True, user_id="user-1",
            )

    assert result.status == "COMPLETED"
    _, kwargs = lb_cls.call_args
    assert kwargs.get("storage_state") == saved


def test_no_user_id_means_no_session_lookup_and_a_fresh_context(tmp_path):
    """A run with no user_id (batch/dispatcher paths that don't have one)
    must not explode calling google_session.get_session(None) -- confirmed
    separately in test_google_session.py, this checks the adapter's own
    wiring stays sane too."""
    with patch("src.applications.adapters.google_forms_adapter.LaunchedBrowser") as lb_cls:
        page = MagicMock(url="https://docs.google.com/forms/d/e/abc/viewform", title=lambda: "Backend Engineer Application")
        lb_cls.return_value.__enter__.return_value = MagicMock(page=page)

        with patch.object(GoogleFormsHandler, "execute", lambda self: {"status": "COMPLETED", "telemetry": {}}), \
             patch("src.applications.adapters.google_forms_adapter.enrich_with_web_search", side_effect=lambda lead: lead):
            result = GoogleFormsAdapter().apply(
                {**_job(), "execution_dir": str(tmp_path)},
                resume_path="/tmp/resume.pdf", profile_manager=MagicMock(), test_mode=True,
            )

    assert result.status == "COMPLETED"
    _, kwargs = lb_cls.call_args
    assert kwargs.get("storage_state") is None
