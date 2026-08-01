-- Migration 003: Provider-Specific Registries for Indian ATS Platforms
-- Strictly mirrors existing registry_greenhouse, registry_lever, etc. conventions

CREATE TABLE IF NOT EXISTS registry_darwinbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT UNIQUE NOT NULL,
    company_name TEXT,
    endpoint TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry_darwinbox_state (
    company_id TEXT PRIMARY KEY,
    last_successful_crawl TIMESTAMP,
    next_check_at REAL DEFAULT 0.0,
    crawl_status TEXT DEFAULT 'QUEUED',
    failure_count INTEGER DEFAULT 0,
    job_count INTEGER DEFAULT 0,
    reservation_token TEXT,
    reserved_until REAL
);

CREATE TABLE IF NOT EXISTS registry_freshteam (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT UNIQUE NOT NULL,
    company_name TEXT,
    endpoint TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry_freshteam_state (
    company_id TEXT PRIMARY KEY,
    last_successful_crawl TIMESTAMP,
    next_check_at REAL DEFAULT 0.0,
    crawl_status TEXT DEFAULT 'QUEUED',
    failure_count INTEGER DEFAULT 0,
    job_count INTEGER DEFAULT 0,
    reservation_token TEXT,
    reserved_until REAL
);

CREATE TABLE IF NOT EXISTS registry_keka (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT UNIQUE NOT NULL,
    company_name TEXT,
    endpoint TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry_keka_state (
    company_id TEXT PRIMARY KEY,
    last_successful_crawl TIMESTAMP,
    next_check_at REAL DEFAULT 0.0,
    crawl_status TEXT DEFAULT 'QUEUED',
    failure_count INTEGER DEFAULT 0,
    job_count INTEGER DEFAULT 0,
    reservation_token TEXT,
    reserved_until REAL
);

CREATE TABLE IF NOT EXISTS registry_zoho_recruit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT UNIQUE NOT NULL,
    company_name TEXT,
    endpoint TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS registry_zoho_recruit_state (
    company_id TEXT PRIMARY KEY,
    last_successful_crawl TIMESTAMP,
    next_check_at REAL DEFAULT 0.0,
    crawl_status TEXT DEFAULT 'QUEUED',
    failure_count INTEGER DEFAULT 0,
    job_count INTEGER DEFAULT 0,
    reservation_token TEXT,
    reserved_until REAL
);
