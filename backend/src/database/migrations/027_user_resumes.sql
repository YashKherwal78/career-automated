-- Migration 027: User Resumes
--
-- Backs POST /users/extract_profile and /users/upload_resume (see users.py),
-- which have written to this table since it was added but the table itself
-- was never migrated. No FK to auth.users — see migration 022's note.

CREATE TABLE IF NOT EXISTS public.user_resumes (
    user_id UUID PRIMARY KEY,
    resume_url TEXT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
