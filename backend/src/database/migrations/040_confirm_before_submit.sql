-- Opt-in: pause once, right before the final submit click, and hand the
-- real (not headless) browser window to the user for a final look before
-- it goes out -- same live-view mechanism already built for CAPTCHAs
-- (src/applications/captcha_bridge.py), just triggered unconditionally
-- instead of only when a challenge blocks progress. Built for mobile
-- users (no browser extension there -- see manifest limitations on
-- iOS/Android), but works for anyone on "automatic" apply mode who wants
-- a final look. Defaults FALSE: the existing "submit immediately, only
-- pause for a real CAPTCHA" behavior is unchanged for anyone who doesn't
-- turn this on.
ALTER TABLE public.user_application_policies
    ADD COLUMN IF NOT EXISTS confirm_before_submit BOOLEAN NOT NULL DEFAULT FALSE;
