-- POST /{job_id}/apply's dedupe check (SELECT for an existing row) and its
-- write (INSERT after the Playwright run, which can take minutes) were not
-- atomic -- two near-simultaneous requests for the same job could both
-- pass the dedupe check before either INSERT landed, letting both proceed
-- to a real submission. This constraint is the backstop: the endpoint now
-- claims a row up front via INSERT ... ON CONFLICT DO NOTHING, and this is
-- what makes the second concurrent claim actually fail instead of racing.
-- Postgres has no "ADD CONSTRAINT IF NOT EXISTS" -- this is the standard
-- idempotent idiom for it.
DO $$
BEGIN
    ALTER TABLE public.application_packages
        ADD CONSTRAINT uq_application_packages_user_job UNIQUE (user_id, job_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
