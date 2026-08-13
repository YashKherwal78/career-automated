-- Cover letters generated as part of a real (non-test-mode) auto-apply
-- submission, for paid-tier users only (src/billing/access.py). Previously
-- cover-letter generation was purely on-demand via POST /resume/cover-letter
-- with no persistence -- this table lets the auto-apply pipeline attach one
-- per real application and lets the user look it up later (e.g. from the
-- Applications page) instead of it only existing for the length of one
-- HTTP response.
CREATE TABLE IF NOT EXISTS public.generated_cover_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    job_id UUID,
    company_name TEXT,
    job_title TEXT,
    cover_letter_text TEXT NOT NULL,
    word_count INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

DO $$
BEGIN
    ALTER TABLE public.generated_cover_letters
        ADD CONSTRAINT uq_generated_cover_letters_user_job UNIQUE (user_id, job_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_generated_cover_letters_user
    ON public.generated_cover_letters (user_id, created_at DESC);
