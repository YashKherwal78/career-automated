-- 011_company_lifecycle_columns.sql
-- Add id and lifecycle_state to company_identities.

ALTER TABLE company_identities ADD COLUMN id SERIAL;
ALTER TABLE company_identities ADD COLUMN lifecycle_state TEXT DEFAULT 'DISCOVERED';
