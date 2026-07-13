-- 012_company_health_columns.sql
-- Add health_state and failure_reason to company_identities.

ALTER TABLE company_identities ADD COLUMN health_state TEXT DEFAULT 'HEALTHY';
ALTER TABLE company_identities ADD COLUMN failure_reason TEXT;
