-- A second, parallel outreach system alongside public.referral_outreach
-- (unchanged) -- see src/referrals/hr_referral_pitch.py. Same-shaped table,
-- deliberately separate rather than adding a column to referral_outreach:
-- keeps the two systems fully independent (one email per job per system,
-- not fighting over the same unique (user_id, job_id) slot), and keeps the
-- original cold-referral-ask system entirely untouched.
CREATE TABLE IF NOT EXISTS public.hr_referral_pitches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    job_id UUID,
    company_name TEXT,
    job_title TEXT,
    contact_name TEXT,
    contact_role TEXT,
    contact_email TEXT,
    email_confidence INT DEFAULT 0,
    discovery_source TEXT,
    -- 'hr_pitch' (direct fit pitch to a recruiter/hiring manager) or
    -- 'referral_ask' (asking a peer/senior IC for a referral) -- see
    -- hr_referral_pitch.py's _mode_for_contact.
    mail_type VARCHAR(20) NOT NULL,
    subject TEXT,
    body TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING_REVIEW',
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE
);

DO $$
BEGIN
    ALTER TABLE public.hr_referral_pitches
        ADD CONSTRAINT uq_hr_referral_pitches_user_job UNIQUE (user_id, job_id);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_hr_referral_pitches_user
    ON public.hr_referral_pitches (user_id, created_at DESC);
