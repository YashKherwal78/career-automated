-- 003_production_scheduling.sql
-- Appends scheduling, prioritization, and task reservation fields to the main pipeline tables

-- Add scheduling fields to ats_registry
ALTER TABLE ats_registry ADD COLUMN priority INTEGER DEFAULT 10;
ALTER TABLE ats_registry ADD COLUMN next_check_at REAL DEFAULT 0.0;
ALTER TABLE ats_registry ADD COLUMN reservation_token TEXT;
ALTER TABLE ats_registry ADD COLUMN reserved_by TEXT;
ALTER TABLE ats_registry ADD COLUMN reserved_until REAL DEFAULT 0.0;
ALTER TABLE ats_registry ADD COLUMN failure_count INTEGER DEFAULT 0;

-- Add same scheduling columns to company_identities for discovery scheduling
ALTER TABLE company_identities ADD COLUMN next_discovery_at REAL DEFAULT 0.0;
ALTER TABLE company_identities ADD COLUMN discovery_reservation_token TEXT;
ALTER TABLE company_identities ADD COLUMN discovery_reserved_by TEXT;
ALTER TABLE company_identities ADD COLUMN discovery_reserved_until REAL DEFAULT 0.0;

-- Add same scheduling columns to career_endpoints for verification scheduling
ALTER TABLE career_endpoints ADD COLUMN next_verification_at REAL DEFAULT 0.0;
ALTER TABLE career_endpoints ADD COLUMN verification_reservation_token TEXT;
ALTER TABLE career_endpoints ADD COLUMN verification_reserved_by TEXT;
ALTER TABLE career_endpoints ADD COLUMN verification_reserved_until REAL DEFAULT 0.0;
