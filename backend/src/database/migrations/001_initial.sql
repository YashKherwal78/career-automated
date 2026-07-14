-- 001_initial.sql
-- Base table definitions for company_identities, users, user_profiles, etc.

CREATE TABLE IF NOT EXISTS company_identities (
    company_id TEXT PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,
    canonical_name TEXT NOT NULL,
    legal_name TEXT,
    website TEXT,
    linkedin_url TEXT,
    founders TEXT,
    investors TEXT,
    aliases TEXT,
    lifecycle_state TEXT DEFAULT 'DISCOVERED',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    active_profile TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
    profile_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    profile_name TEXT NOT NULL,
    config_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
