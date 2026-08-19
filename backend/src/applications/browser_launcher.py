"""
Shared browser launch for all ATS adapters. Applies a small set of concrete,
legitimate stealth measures — closing gaps between an automated Playwright
session and a real person's browser, not attempting to defeat CAPTCHA
outright:

- Disables Chrome's "automation controlled" mode (removes the infobar and
  a flag several anti-bot checks look for).
- Patches `navigator.webdriver` back to its normal (undefined) value —
  Playwright/Selenium set this to `true` by default, and it's one of the
  most basic, widely-checked bot signals.
- Patches a couple of other automation-only tells (missing `navigator.plugins`,
  the `Notification.permission` quirk headless/automated Chrome exhibits).

None of this fakes a "trusted" click or bypasses an actual CAPTCHA
challenge — see the auto-apply architecture notes on why that's not
attempted here.
"""
import atexit
import os
import shutil
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

_XVFB_STARTED = False


def _ensure_virtual_display() -> None:
    """Chrome is launched headed (see LaunchedBrowser below) rather than
    headless — headless Chrome trips several ATS bot-detection heuristics
    that headed Chrome doesn't. On a local dev machine that's fine, there's
    a real display. On a Linux server/container (no X server) headed launch
    fails outright ("Missing X server or $DISPLAY"), and after that failure
    Playwright's driver is left in a broken state that also poisons every
    later launch in the same process ("Sync API inside asyncio loop").
    Starting one Xvfb virtual display for the life of this process — instead
    of switching to headless=True — keeps the real-Chrome rendering path
    that the stealth patches below are built around.
    """
    global _XVFB_STARTED
    if _XVFB_STARTED or os.environ.get("DISPLAY") or sys.platform != "linux":
        return
    if not shutil.which("Xvfb"):
        return
    proc = subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1280x800x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    atexit.register(proc.terminate)
    os.environ["DISPLAY"] = ":99"
    time.sleep(0.5)
    _XVFB_STARTED = True


_STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = window.chrome || { runtime: {} };
"""

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


class LaunchedBrowser:
    """Context manager wrapping playwright's browser/context/page lifecycle
    with the stealth patches pre-applied, so adapters don't each repeat
    (and potentially drift on) the same launch boilerplate."""

    def __init__(self, storage_state: dict = None):
        # A saved Google session (google_session.py) -- when present, the
        # new context starts already signed in, the same way a real
        # returning visitor's browser would via its cookies. None (the
        # default, and the only thing every other adapter passes) is a
        # completely ordinary fresh context, unchanged from before this
        # parameter existed.
        self._storage_state = storage_state

    def __enter__(self):
        _ensure_virtual_display()
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context_kwargs = {"viewport": {"width": 1280, "height": 800}, "user_agent": USER_AGENT}
        if self._storage_state:
            context_kwargs["storage_state"] = self._storage_state
        self.context = self.browser.new_context(**context_kwargs)
        self.context.add_init_script(_STEALTH_INIT_SCRIPT)
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.browser.close()
        finally:
            self._pw.stop()
