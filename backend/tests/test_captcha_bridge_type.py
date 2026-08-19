"""
The "type" relay command added to captcha_bridge.py for the google_connect
flow -- request_click has no equivalent for real text entry (there's no
coordinate to "type" at), which Google's email/password/2FA fields need.
Click and resolved/skip already had coverage-by-usage elsewhere; this is
the one genuinely new code path in the module.
"""
import threading
import time
from unittest.mock import MagicMock

from src.applications import captcha_bridge


def test_request_type_relays_text_to_page_keyboard_and_returns_true():
    session_id = captcha_bridge.create_session("user-1", "job-1", reason="google_connect")
    page = MagicMock()

    worker = threading.Thread(
        target=captcha_bridge.wait_for_human, args=(session_id, page), kwargs={"timeout_seconds": 5}
    )
    worker.start()
    time.sleep(0.05)  # let wait_for_human start pulling from cmd_queue

    ok = captcha_bridge.request_type(session_id, "candidate@gmail.com")

    assert ok is True
    page.keyboard.type.assert_called_once_with("candidate@gmail.com")

    captcha_bridge.signal_resolved(session_id)
    worker.join(timeout=5)


def test_request_type_returns_false_when_keyboard_type_raises():
    session_id = captcha_bridge.create_session("user-1", "job-1", reason="google_connect")
    page = MagicMock()
    page.keyboard.type.side_effect = RuntimeError("page closed")

    worker = threading.Thread(
        target=captcha_bridge.wait_for_human, args=(session_id, page), kwargs={"timeout_seconds": 5}
    )
    worker.start()
    time.sleep(0.05)

    ok = captcha_bridge.request_type(session_id, "candidate@gmail.com")

    assert ok is False

    captcha_bridge.signal_resolved(session_id)
    worker.join(timeout=5)


def test_request_type_on_an_unknown_session_returns_false_without_raising():
    assert captcha_bridge.request_type("nonexistent-session", "hello") is False


def test_resolved_after_a_type_command_still_returns_true():
    """Confirms "type" doesn't fall through and terminate the loop the way
    a missing case in the if/elif chain would -- wait_for_human must keep
    waiting for an explicit resolved/skip/timeout afterwards."""
    session_id = captcha_bridge.create_session("user-1", "job-1", reason="google_connect")
    page = MagicMock()
    result = {}

    def run():
        result["resolved"] = captcha_bridge.wait_for_human(session_id, page, timeout_seconds=5)

    worker = threading.Thread(target=run)
    worker.start()
    time.sleep(0.05)

    captcha_bridge.request_type(session_id, "hunter2")
    captcha_bridge.signal_resolved(session_id)
    worker.join(timeout=5)

    assert result["resolved"] is True
