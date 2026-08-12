-- Both apply paths already exist (server-side batch automation, and the
-- browser-extension-driven assisted flow) but nothing tied them together
-- as an actual user choice -- this is that choice. 'automatic': runs
-- server-side, costs compute, hits the live-view CAPTCHA flow when needed.
-- 'assisted': matched jobs surface an "Open & Autofill" action instead of
-- ever being dispatched server-side -- runs on the user's own machine/IP,
-- free, but needs their presence.
ALTER TABLE public.user_application_policies
    ADD COLUMN IF NOT EXISTS apply_mode VARCHAR(20) NOT NULL DEFAULT 'automatic';
