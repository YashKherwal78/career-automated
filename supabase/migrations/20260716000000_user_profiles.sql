-- Drop legacy empty user_profiles table if it exists
DROP TABLE IF EXISTS public.user_profiles CASCADE;
DROP TABLE IF EXISTS public.user_education CASCADE;
DROP TABLE IF EXISTS public.user_experience CASCADE;
DROP TABLE IF EXISTS public.user_skills CASCADE;
DROP TABLE IF EXISTS public.user_resumes CASCADE;

-- Create public.user_profiles table
CREATE TABLE public.user_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    avatar_url TEXT,
    onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    career_goals TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create public.user_education table
CREATE TABLE public.user_education (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(user_id) ON DELETE CASCADE NOT NULL,
    institution TEXT NOT NULL,
    degree TEXT,
    field_of_study TEXT,
    start_year INT,
    end_year INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create public.user_experience table
CREATE TABLE public.user_experience (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(user_id) ON DELETE CASCADE NOT NULL,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create public.user_skills table
CREATE TABLE public.user_skills (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(user_id) ON DELETE CASCADE NOT NULL,
    skill_name TEXT NOT NULL,
    proficiency TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create public.user_resumes table
CREATE TABLE public.user_resumes (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES public.user_profiles(user_id) ON DELETE CASCADE NOT NULL,
    resume_url TEXT NOT NULL,
    file_name TEXT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_education ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_experience ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_skills ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_resumes ENABLE ROW LEVEL SECURITY;

-- Create Policies for RLS
CREATE POLICY "Users can manage their own profile" ON public.user_profiles
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own education" ON public.user_education
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own experience" ON public.user_experience
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own skills" ON public.user_skills
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own resumes" ON public.user_resumes
    USING (auth.uid() = user_id);

-- Create a function to handle new user signups
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (user_id, email, full_name, avatar_url, onboarding_complete)
    VALUES (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', ''),
        coalesce(new.raw_user_meta_data->>'avatar_url', ''),
        FALSE
    )
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger on auth.users for signup automation
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
