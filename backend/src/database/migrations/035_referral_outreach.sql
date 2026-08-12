-- The existing referral-contact-finding pipeline (src/referrals/) is real
-- and works (JD email parsing -> DuckDuckGo X-ray -> Hunter.io domain
-- search), but writes to a separate local SQLite CRM file (src/crm/database.py)
-- disconnected from the production Postgres DB everything else runs on --
-- unusable from the actual apply flow. This ports the contact record into
-- Postgres and adds the draft/review/send state a real per-user, per-
-- application referral email needs (the SQLite version had no such
-- concept -- it was a standalone contact-discovery tool, not wired to any
-- application).

CREATE TABLE IF NOT EXISTS public.referral_outreach (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    job_id UUID,
    company_name TEXT NOT NULL,
    job_title TEXT,
    contact_name TEXT NOT NULL,
    contact_role TEXT,
    contact_email TEXT,
    email_confidence INTEGER DEFAULT 0,
    discovery_source TEXT,
    subject TEXT,
    body TEXT,
    -- PENDING_REVIEW: drafted, waiting on the user to approve/reject.
    -- APPROVED: user approved, queued to send (or sent immediately once
    -- auto-send is turned on for this user).
    -- SENT / REJECTED / FAILED: terminal states.
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING_REVIEW',
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_referral_outreach_user_status
    ON public.referral_outreach (user_id, status);

-- Never draft twice for the exact same job -- one referral attempt per
-- application, not one per contact-discovery run.
CREATE UNIQUE INDEX IF NOT EXISTS idx_referral_outreach_user_job
    ON public.referral_outreach (user_id, job_id) WHERE job_id IS NOT NULL;

-- Durable per-user on/off switch for auto-send, same pattern as
-- user_application_policies.enabled for auto-apply -- starts everyone in
-- review-only mode; a user flips this once they trust the drafts.
ALTER TABLE public.user_application_policies
    ADD COLUMN IF NOT EXISTS referral_auto_send BOOLEAN NOT NULL DEFAULT FALSE;
