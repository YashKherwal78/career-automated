-- Precomputed corpus document-frequency per lexeme, over normalized_jobs.search_vector.
-- Used by candidate_term_selection.py to rank non-canonical BM25 query terms
-- by real discriminative power instead of raw string length. Deliberately a
-- separate, periodically-refreshed table rather than a live ts_stat() call --
-- ts_stat() scans the whole search_vector column, and this project has
-- already had two separate production incidents from a per-request query
-- touching the full 1.5M-row table (see repository.py's get_jobs_by_hybrid_search
-- comments). Refreshed by scripts/refresh_term_document_frequency.py, not on
-- any request path.
CREATE TABLE IF NOT EXISTS public.term_document_frequency (
    term TEXT PRIMARY KEY,
    doc_count INT NOT NULL,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
