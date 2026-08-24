-- Additive structured candidate representation, computed at profile-save
-- time (not per /jobs request). Sits alongside profile_data, does not
-- replace it -- nothing existing reads this column, so it's safe to add
-- without touching any current behavior. See
-- discovery/candidate_understanding/role_profiles.py for what gets stored
-- here (capability.role_profiles + intent, separated per the same
-- distinction jie/candidate_profile.py's target_roles-vs-career_preferences
-- logic already makes, just made explicit and structured).
ALTER TABLE public.user_career_profiles
    ADD COLUMN IF NOT EXISTS structured_profile JSONB DEFAULT '{}'::jsonb;
