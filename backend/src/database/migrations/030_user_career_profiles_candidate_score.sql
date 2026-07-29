-- The live user_career_profiles table pre-dates migration 024's CREATE TABLE
-- definition, so its "candidate_score" column was never added (CREATE TABLE
-- IF NOT EXISTS is a no-op against an existing table). Every PUT
-- /candidate/profile call has been failing in production because of this.
ALTER TABLE public.user_career_profiles ADD COLUMN IF NOT EXISTS candidate_score INT DEFAULT 75;
