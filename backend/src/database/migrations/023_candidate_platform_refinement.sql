-- Migration 023: Candidate Platform Architecture Refinements

-- 1. Immutable Resume Version Manager
CREATE TABLE IF NOT EXISTS public.user_resume_versions_v2 (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    parent_version_id UUID REFERENCES public.user_resume_versions_v2(version_id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    version_type VARCHAR(50) NOT NULL DEFAULT 'BASE', -- 'BASE' or 'TAILORED'
    target_job_id UUID,
    selected_experience_ids JSONB DEFAULT '[]'::jsonb,
    selected_project_ids JSONB DEFAULT '[]'::jsonb,
    selected_skills JSONB DEFAULT '[]'::jsonb,
    bullet_overrides JSONB DEFAULT '{}'::jsonb,
    is_immutable BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Optimization Sessions (Tracks Accept/Reject Choices)
CREATE TABLE IF NOT EXISTS public.user_optimization_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL,
    source_version_id UUID REFERENCES public.user_resume_versions_v2(version_id) ON DELETE SET NULL,
    suggested_edits JSONB DEFAULT '[]'::jsonb,
    accepted_edit_ids JSONB DEFAULT '[]'::jsonb,
    rejected_edit_ids JSONB DEFAULT '[]'::jsonb,
    output_version_id UUID REFERENCES public.user_resume_versions_v2(version_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Rendered Artifacts Store
CREATE TABLE IF NOT EXISTS public.user_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    version_id UUID REFERENCES public.user_resume_versions_v2(version_id) ON DELETE CASCADE,
    format VARCHAR(20) NOT NULL, -- 'PDF', 'DOCX', 'HTML', 'JSON'
    storage_url TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Generic Policy Engine Configs
CREATE TABLE IF NOT EXISTS public.user_policy_engine (
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    policy_type VARCHAR(50) NOT NULL, -- 'APPLICATION', 'MATCHING', 'EMAIL', 'RESUME'
    policy_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, policy_type)
);
