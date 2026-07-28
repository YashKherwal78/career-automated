-- Migration 028: Onboarding detail tables (education / experience / skills)
--
-- Backs PUT /users/onboarding (see users.py complete_onboarding). These tables
-- were referenced by that endpoint but never migrated anywhere — every
-- onboarding completion was failing with "relation does not exist" before
-- ever reaching the onboarding_complete flag update.
-- No FK to auth.users — see migration 022's note (separate Postgres instance).

CREATE TABLE IF NOT EXISTS public.user_education (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    institution VARCHAR(255) NOT NULL,
    degree VARCHAR(255),
    field_of_study VARCHAR(255),
    start_year INT,
    end_year INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.user_experience (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    company VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    start_date VARCHAR(50),
    end_date VARCHAR(50),
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.user_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    proficiency VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_education_user_id ON public.user_education(user_id);
CREATE INDEX IF NOT EXISTS idx_user_experience_user_id ON public.user_experience(user_id);
CREATE INDEX IF NOT EXISTS idx_user_skills_user_id ON public.user_skills(user_id);
