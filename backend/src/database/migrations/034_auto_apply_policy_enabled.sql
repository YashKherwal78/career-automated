-- The dashboard's "Start Auto Apply" toggle had nowhere durable to store
-- on/off state -- it lived only in frontend useState, so a page reload
-- reset it to "off" even while a batch-apply run was still going server-
-- side (or, worse, made a genuinely-off state look like it needed
-- re-enabling). user_application_policies already exists for exactly this
-- kind of per-user auto-apply setting; it just never had an on/off flag.

ALTER TABLE public.user_application_policies
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT FALSE;
