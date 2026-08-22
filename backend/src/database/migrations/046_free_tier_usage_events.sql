-- Per-user daily usage tracking for free-tier rate limits on generation
-- endpoints (resume tailoring, cover letters). One row per successful
-- generation; the limit itself is a UTC-day COUNT(*) filter done in
-- Python (src/billing/usage_limits.py), not enforced by this table.
-- Paid users (src/billing/access.py::has_paid_access) are never subject
-- to this check, so this table is only ever written to for free-tier
-- requests.
CREATE TABLE IF NOT EXISTS public.free_tier_usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('resume_tailor', 'cover_letter')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_free_tier_usage_events_user_type_day
    ON public.free_tier_usage_events (user_id, event_type, created_at DESC);
