-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create public.documents table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace VARCHAR(255) NOT NULL,
    source_type VARCHAR(255) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    checksum VARCHAR(255),
    version INT DEFAULT 1 NOT NULL,
    is_latest BOOLEAN DEFAULT TRUE NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' NOT NULL,
    embedding_provider VARCHAR(255) NOT NULL,
    embedding_model VARCHAR(255) NOT NULL,
    embedding_dimension INT NOT NULL,
    distance_metric VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Create public.vector_chunks table
CREATE TABLE IF NOT EXISTS public.vector_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    owner_type VARCHAR(255) NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    chunk_index INT NOT NULL DEFAULT 0,
    chunk_checksum VARCHAR(255) NOT NULL,
    chunk_metadata JSONB DEFAULT '{}'::jsonb NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536), -- Explicitly constrained to Gemini default dimensions
    embedding_type VARCHAR(50) DEFAULT 'semantic' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_documents_namespace ON public.documents(namespace);
CREATE INDEX IF NOT EXISTS idx_documents_source ON public.documents(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_vector_chunks_owner ON public.vector_chunks(owner_type, owner_id);

-- HNSW vector cosine similarity index
CREATE INDEX IF NOT EXISTS idx_vector_chunks_embedding ON public.vector_chunks USING hnsw (embedding vector_cosine_ops);
