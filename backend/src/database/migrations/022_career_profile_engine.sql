-- Migration 022: Career Profile Engine & Resume Versioning Infrastructure
--
-- user_id columns intentionally have NO foreign key to auth.users: Supabase auth
-- lives in a separate Postgres instance from this operational database, so a
-- same-database FK constraint can't reference it. Identity is enforced upstream
-- by JWT verification in get_current_user(), not by the DB.

-- 1. Canonical Career Profile Store (Single Source of Truth for Candidate Data)
CREATE TABLE IF NOT EXISTS public.user_career_profiles (
    user_id UUID PRIMARY KEY,
    profile_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    completeness_score INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Resume Version Manager (Base and Tailored Resume Variants)
CREATE TABLE IF NOT EXISTS public.user_resume_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    name VARCHAR(255) NOT NULL,
    version_type VARCHAR(50) NOT NULL DEFAULT 'BASE', -- 'BASE' or 'TAILORED'
    target_job_id UUID,
    selected_experience_ids JSONB DEFAULT '[]'::jsonb,
    selected_project_ids JSONB DEFAULT '[]'::jsonb,
    selected_skills JSONB DEFAULT '[]'::jsonb,
    bullet_overrides JSONB DEFAULT '{}'::jsonb,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Application Packages (Consumed by Auto Apply)
CREATE TABLE IF NOT EXISTS public.application_packages (
    package_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    job_id UUID NOT NULL,
    resume_version_id UUID REFERENCES public.user_resume_versions(version_id) ON DELETE SET NULL,
    cover_letter_text TEXT,
    screening_answers JSONB DEFAULT '{}'::jsonb,
    portfolio_links JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'APPROVED', 'SUBMITTED'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. User Application Policies (Configurable Policy Engine for Auto Apply)
CREATE TABLE IF NOT EXISTS public.user_application_policies (
    user_id UUID PRIMARY KEY,
    minimum_match_score INT DEFAULT 80,
    tailor_resume BOOLEAN DEFAULT TRUE,
    generate_cover_letter VARCHAR(50) DEFAULT 'AUTO',
    require_approval_if JSONB DEFAULT '["score < 85", "relocation_required"]'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
