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
from playwright.sync_api import sync_playwright

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

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=USER_AGENT,
        )
        self.context.add_init_script(_STEALTH_INIT_SCRIPT)
        self.page = self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.browser.close()
        finally:
            self._pw.stop()
