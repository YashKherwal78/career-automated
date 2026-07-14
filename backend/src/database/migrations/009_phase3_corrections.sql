-- Migration for Phase 3 Pipeline Corrections
-- Adds crawl_status and verification_method to company_identities

ALTER TABLE company_identities ADD COLUMN IF NOT EXISTS crawl_status TEXT;
ALTER TABLE company_identities ADD COLUMN IF NOT EXISTS verification_method TEXT;
