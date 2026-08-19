"""
Lets a FastAPI request (running on a threadpool thread) drive the live
Playwright `page` object a background application run is paused on,
without ever calling Playwright from a thread other than the one that
created it -- Playwright's sync API is not thread-safe across threads, so
a request handler calling page.screenshot() directly would be operating on
the wrong thread. Commands are relayed through thread-safe queues instead:
the batch-apply thread (which owns `page`) executes them; the API thread
just pushes a command and waits for the result.

This is the actual, working replacement for _wait_for_human_captcha_resolution's
previous `input()` call, which only ever worked when someone ran this
locally with a terminal in front of them -- see base_handler.py.
"""
import queue
import threading
import time
import uuid
from typing import Optional

_SESSIONS: dict[str, dict] = {}
_LOCK = threading.Lock()

# Maps user_id -> currently-active captcha session_id, so the frontend can
# discover "is there something waiting on me right now" without needing to
# already know a session_id.
_ACTIVE_BY_USER: dict[str, str] = {}


def create_session(user_id: str, job_id: str, reason: str = "captcha") -> str:
    """reason is "captcha" (a real challenge blocked progress) or
    "final_review" (nothing's blocking -- this is the confirm-before-submit
    checkpoint, same mechanism, different purpose) -- lets the frontend
    show the right copy without needing a second endpoint/session type."""
    session_id = str(uuid.uuid4())
    with _LOCK:
        _SESSIONS[session_id] = {
            "user_id": user_id,
            "job_id": job_id,
            "reason": reason,
            "cmd_queue": queue.Queue(),
            "result_queue": queue.Queue(),
            "created_at": time.time(),
        }
        _ACTIVE_BY_USER[user_id] = session_id
    return session_id


def end_session(session_id: str):
    with _LOCK:
        session = _SESSIONS.pop(session_id, None)
        if session and _ACTIVE_BY_USER.get(session["user_id"]) == session_id:
            _ACTIVE_BY_USER.pop(session["user_id"], None)


def get_session(session_id: str) -> Optional[dict]:
    with _LOCK:
        return _SESSIONS.get(session_id)


def get_active_session_id_for_user(user_id: str) -> Optional[str]:
    with _LOCK:
        session_id = _ACTIVE_BY_USER.get(user_id)
        return session_id if session_id in _SESSIONS else None


def request_screenshot(session_id: str, timeout: float = 8.0) -> Optional[bytes]:
    session = get_session(session_id)
    if not session:
        return None
    session["cmd_queue"].put({"type": "screenshot"})
    try:
        return session["result_queue"].get(timeout=timeout)
    except queue.Empty:
        return None


def request_click(session_id: str, x: float, y: float, timeout: float = 8.0) -> bool:
    session = get_session(session_id)
    if not session:
        return False
    session["cmd_queue"].put({"type": "click", "x": x, "y": y})
    try:
        return bool(session["result_queue"].get(timeout=timeout))
    except queue.Empty:
        return False


def request_type(session_id: str, text: str, timeout: float = 8.0) -> bool:
    """Types into whatever element currently has focus on the live page --
    there's no click-target coordinate for typing the way there is for
    request_click, so the operator is expected to have already clicked the
    field first. Needed for the google_connect flow (email/password/2FA
    entry); unused by the plain CAPTCHA/final_review reasons, which never
    need real text input."""
    session = get_session(session_id)
    if not session:
        return False
    session["cmd_queue"].put({"type": "type", "text": text})
    try:
        return bool(session["result_queue"].get(timeout=timeout))
    except queue.Empty:
        return False


def signal_resolved(session_id: str) -> bool:
    session = get_session(session_id)
    if not session:
        return False
    session["cmd_queue"].put({"type": "resolved"})
    return True


def signal_skip(session_id: str) -> bool:
    session = get_session(session_id)
    if not session:
        return False
    session["cmd_queue"].put({"type": "skip"})
    return True


def wait_for_human(session_id: str, page, timeout_seconds: int = 600) -> bool:
    """Runs on the SAME thread as `page` -- executes screenshot/click
    commands pushed by API endpoints from other threads via the thread-safe
    queues above. Returns True if the operator signaled "resolved", False
    on "skip" or timeout (both route to REVIEW_REQUIRED same as before)."""
    session = get_session(session_id)
    if not session:
        return False
    cmd_q = session["cmd_queue"]
    deadline = time.time() + timeout_seconds
    try:
        while time.time() < deadline:
            try:
                cmd = cmd_q.get(timeout=0.5)
            except queue.Empty:
                continue
            ctype = cmd.get("type")
            if ctype == "screenshot":
                try:
                    session["result_queue"].put(page.screenshot(type="png"))
                except Exception:
                    session["result_queue"].put(None)
            elif ctype == "click":
                try:
                    page.mouse.click(cmd["x"], cmd["y"])
                    session["result_queue"].put(True)
                except Exception:
                    session["result_queue"].put(False)
            elif ctype == "type":
                try:
                    page.keyboard.type(cmd["text"])
                    session["result_queue"].put(True)
                except Exception:
                    session["result_queue"].put(False)
            elif ctype == "resolved":
                return True
            elif ctype == "skip":
                return False
        return False
    finally:
        end_session(session_id)
