-- Migration 024: Simplified V1 Candidate-First Architecture

-- 1. Candidate Profile Table (Permanent Source of Truth)
CREATE TABLE IF NOT EXISTS public.user_career_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidate_score INT DEFAULT 75, -- Evaluated candidate strength score
    completeness_score INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Base Resume Record (Original Upload or Builder Base Document)
CREATE TABLE IF NOT EXISTS public.user_base_resumes (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    file_name VARCHAR(255),
    storage_url TEXT,
    raw_parsed_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Application Submissions Tracker (Clean, Un-duplicated Record)
CREATE TABLE IF NOT EXISTS public.user_applications (
    application_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'APPLIED', -- 'QUEUED', 'APPLIED', 'INTERVIEWING', 'REJECTED'
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    answers_submitted JSONB DEFAULT '{}'::jsonb
);
