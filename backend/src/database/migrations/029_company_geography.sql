-- Migration 029: Real geography tracking for company_identities
--
-- company_identities had no country/region/city column at all — the only
-- place location data ever lived was buried in the free-text `aliases` JSON
-- blob (and only for the DPIIT import path, which never actually ran). This
-- made it impossible to query/prioritize company discovery by geography,
-- which matters given the candidate base is India-heavy while job coverage
-- there is currently ~2% of active jobs.

ALTER TABLE public.company_identities ADD COLUMN IF NOT EXISTS country VARCHAR(100);
ALTER TABLE public.company_identities ADD COLUMN IF NOT EXISTS region VARCHAR(100);
ALTER TABLE public.company_identities ADD COLUMN IF NOT EXISTS city VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_company_identities_country ON public.company_identities(country);
