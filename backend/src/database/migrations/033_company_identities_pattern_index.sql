-- Supports prefix-range lookups on company_identities.company_id
-- (e.g. "adobe" matching "adobe-workday") used by the LATERAL fallback
-- join in job/repository.py. Uses text_pattern_ops so the ~>=~ / ~<~
-- pattern-comparison operators in that query get an index scan instead
-- of a per-row Seq Scan. Plain >=/< would need the same opclass too, but
-- also break under the default (non-C) collation, which treats '-' as
-- low-weight and misorders "alight-com-x" relative to "alight-"/"alight.".
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_company_identities_id_pattern
    ON company_identities (company_id text_pattern_ops);
