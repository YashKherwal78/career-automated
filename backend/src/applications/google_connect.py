"""
Establishes the one thing an OAuth token can't: a real, signed-in Google
web session, captured from a live browser the candidate logs into
themselves via the same screenshot/click(/type) relay captcha_bridge.py
already uses for CAPTCHA handoffs. On success, the resulting
storage_state() is persisted (google_session.py) and GoogleFormsAdapter
reuses it on future sign-in-gated Google Forms instead of asking the
candidate to log in per application.

Runs on its own daemon thread: wait_for_human blocks for up to 10 minutes
and owns the Playwright `page` object for that whole time (Playwright's
sync API isn't safe to call from any thread other than the one that
created it), so this can't run on the request-handling thread the way a
simple "start" call would suggest.
"""
import threading

from src.applications import captcha_bridge, google_session
from src.applications.browser_launcher import LaunchedBrowser
from src.system.logger import setup_logger

logger = setup_logger("google_connect")

_SIGNIN_URL = "https://accounts.google.com/ServiceLogin"


def _run(user_id: str):
    try:
        with LaunchedBrowser() as lb:
            page = lb.page
            try:
                page.goto(_SIGNIN_URL, timeout=30000)
            except Exception as e:
                logger.info(f"google_connect: navigation to sign-in failed for user {user_id}: {e}")
                return

            session_id = captcha_bridge.create_session(user_id, job_id="", reason="google_connect")
            logger.info(f"google_connect: live session {session_id} opened for user {user_id}")

            resolved = captcha_bridge.wait_for_human(session_id, page, timeout_seconds=600)
            if not resolved:
                logger.info(f"google_connect: user {user_id} cancelled or timed out without connecting.")
                return

            try:
                state = page.context.storage_state()
            except Exception as e:
                logger.info(f"google_connect: could not capture session state for user {user_id}: {e}")
                return

            google_session.save_session(user_id, state)
            logger.info(f"google_connect: session saved for user {user_id}")
    except Exception as e:
        logger.info(f"google_connect: browser launch failed for user {user_id}: {e}")


def start_connect_flow(user_id: str):
    """Fire-and-forget -- the caller (the API endpoint) returns immediately;
    the frontend discovers the live session the same way it discovers a
    CAPTCHA handoff, by polling GET /captcha/active."""
    threading.Thread(target=_run, args=(user_id,), daemon=True).start()
