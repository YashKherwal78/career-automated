-- Migration 010: Endpoint Intelligence
-- Description: Adds tables and enums for discovery confidence scoring and permanent candidate tracking.

BEGIN;

CREATE TYPE endpoint_lifecycle_enum AS ENUM (
    'DISCOVERED',
    'VERIFIED',
    'ACTIVE',
    'UNHEALTHY',
    'ARCHIVED'
);

CREATE TYPE discovery_source_enum AS ENUM (
    'KNOWN_PATTERN',
    'REGEX',
    'SEARCH_ENGINE',
    'FIRECRAWL',
    'SITEMAP',
    'ROBOTS_TXT',
    'REDIRECT',
    'META_TAGS',
    'EXISTING_DATASET',
    'MANUAL'
);

CREATE TYPE registry_change_reason_enum AS ENUM (
    'INITIAL_DISCOVERY',
    'HIGHER_CONFIDENCE_FOUND',
    'ENDPOINT_MIGRATION',
    'MANUAL_OVERRIDE',
    'ENDPOINT_DIED'
);

CREATE TYPE crawl_strategy_enum AS ENUM (
    'HTML',
    'JSON_API',
    'GRAPHQL',
    'RSS',
    'SITEMAP',
    'PLAYWRIGHT',
    'FIRECRAWL'
);

CREATE TABLE ats_providers (
    provider_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    detector_class TEXT,
    crawler_class TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial providers
INSERT INTO ats_providers (provider_id, display_name, detector_class, crawler_class) VALUES
    ('greenhouse', 'Greenhouse', 'GreenhouseSignature', 'GreenhouseCrawler'),
    ('lever', 'Lever', 'LeverSignature', 'LeverCrawler'),
    ('workday', 'Workday', 'WorkdaySignature', 'WorkdayCrawler'),
    ('ashby', 'Ashby', 'AshbySignature', 'AshbyCrawler'),
    ('smartrecruiters', 'SmartRecruiters', 'SmartRecruitersSignature', 'SmartRecruitersCrawler'),
    ('avature', 'Avature', 'AvatureSignature', 'AvatureCrawler'),
    ('breezy', 'Breezy', 'BreezySignature', 'BreezyCrawler'),
    ('successfactors', 'SuccessFactors', 'SuccessFactorsSignature', 'SuccessFactorsCrawler');

CREATE TABLE endpoint_candidates (
    candidate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT REFERENCES company_identities(company_id),
    provider_id TEXT REFERENCES ats_providers(provider_id),
    url TEXT NOT NULL,
    
    discovery_source discovery_source_enum NOT NULL,
    evidence JSONB,
    crawl_strategy crawl_strategy_enum,
    
    confidence_score SMALLINT NOT NULL,
    health_score SMALLINT DEFAULT 100,
    
    lifecycle_state endpoint_lifecycle_enum DEFAULT 'DISCOVERED',
    times_seen INTEGER DEFAULT 1,
    times_verified INTEGER DEFAULT 0,
    times_failed INTEGER DEFAULT 0,
    
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_checked TIMESTAMP WITH TIME ZONE,
    last_verified TIMESTAMP WITH TIME ZONE,
    last_failure_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(company_id, provider_id, url)
);

CREATE INDEX idx_candidates_company ON endpoint_candidates(company_id);
CREATE INDEX idx_candidates_lifecycle ON endpoint_candidates(lifecycle_state);
CREATE INDEX idx_candidates_confidence ON endpoint_candidates(company_id, confidence_score DESC);

UPDATE ats_registry SET ats_type = lower(ats_type);

ALTER TABLE ats_registry RENAME COLUMN ats_type TO provider_id;

INSERT INTO ats_providers (provider_id, display_name)
SELECT DISTINCT provider_id, initcap(provider_id) FROM ats_registry
WHERE provider_id NOT IN (SELECT provider_id FROM ats_providers) AND provider_id IS NOT NULL;

ALTER TABLE ats_registry ADD CONSTRAINT fk_ats_registry_provider FOREIGN KEY (provider_id) REFERENCES ats_providers(provider_id);

ALTER TABLE ats_registry
    ADD COLUMN candidate_id UUID REFERENCES endpoint_candidates(candidate_id),
    ADD COLUMN health_score SMALLINT DEFAULT 100,
    ADD COLUMN confidence_score SMALLINT DEFAULT 100,
    ADD COLUMN success_count INTEGER DEFAULT 0,
    ADD COLUMN last_success TIMESTAMP WITH TIME ZONE,
    ADD COLUMN last_failure TIMESTAMP WITH TIME ZONE,
    ADD COLUMN last_failure_reason TEXT;

CREATE INDEX idx_registry_company ON ats_registry(company_id);

CREATE TABLE registry_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id TEXT REFERENCES company_identities(company_id),
    provider_id TEXT REFERENCES ats_providers(provider_id),
    old_endpoint_url TEXT,
    new_endpoint_url TEXT,
    reason registry_change_reason_enum NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
