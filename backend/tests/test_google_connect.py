"""
google_connect._run's orchestration: launch a browser to Google sign-in,
open a live captcha_bridge session (reason="google_connect"), and on
"resolved" persist the resulting storage_state via google_session.py.
Exercises _run() directly (not the threaded start_connect_flow() wrapper)
so these stay synchronous and deterministic.
"""
from unittest.mock import MagicMock, patch

from src.applications import google_connect


def _launched_browser(page):
    lb = MagicMock()
    lb.__enter__.return_value = MagicMock(page=page)
    lb.__exit__.return_value = False
    return lb


def test_resolved_session_is_captured_and_saved():
    page = MagicMock()
    state = {"cookies": [{"name": "SID", "value": "abc"}], "origins": []}
    page.context.storage_state.return_value = state

    with patch("src.applications.google_connect.LaunchedBrowser", return_value=_launched_browser(page)), \
         patch("src.applications.google_connect.captcha_bridge.create_session", return_value="sess-1") as create_session, \
         patch("src.applications.google_connect.captcha_bridge.wait_for_human", return_value=True) as wait_for_human, \
         patch("src.applications.google_connect.google_session.save_session") as save_session:
        google_connect._run("user-1")

    page.goto.assert_called_once_with(google_connect._SIGNIN_URL, timeout=30000)
    create_session.assert_called_once_with("user-1", job_id="", reason="google_connect")
    wait_for_human.assert_called_once_with("sess-1", page, timeout_seconds=600)
    save_session.assert_called_once_with("user-1", state)


def test_skip_or_timeout_saves_nothing():
    page = MagicMock()

    with patch("src.applications.google_connect.LaunchedBrowser", return_value=_launched_browser(page)), \
         patch("src.applications.google_connect.captcha_bridge.create_session", return_value="sess-1"), \
         patch("src.applications.google_connect.captcha_bridge.wait_for_human", return_value=False), \
         patch("src.applications.google_connect.google_session.save_session") as save_session:
        google_connect._run("user-1")

    save_session.assert_not_called()


def test_navigation_failure_never_opens_a_live_session_or_saves_anything():
    page = MagicMock()
    page.goto.side_effect = RuntimeError("net::ERR_CONNECTION_RESET")

    with patch("src.applications.google_connect.LaunchedBrowser", return_value=_launched_browser(page)), \
         patch("src.applications.google_connect.captcha_bridge.create_session") as create_session, \
         patch("src.applications.google_connect.google_session.save_session") as save_session:
        google_connect._run("user-1")

    create_session.assert_not_called()
    save_session.assert_not_called()


def test_storage_state_capture_failure_does_not_raise_or_save():
    page = MagicMock()
    page.context.storage_state.side_effect = RuntimeError("browser already closed")

    with patch("src.applications.google_connect.LaunchedBrowser", return_value=_launched_browser(page)), \
         patch("src.applications.google_connect.captcha_bridge.create_session", return_value="sess-1"), \
         patch("src.applications.google_connect.captcha_bridge.wait_for_human", return_value=True), \
         patch("src.applications.google_connect.google_session.save_session") as save_session:
        google_connect._run("user-1")  # must not raise

    save_session.assert_not_called()


def test_browser_launch_failure_is_swallowed_not_raised():
    with patch("src.applications.google_connect.LaunchedBrowser", side_effect=RuntimeError("no display")):
        google_connect._run("user-1")  # must not raise
