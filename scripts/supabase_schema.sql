-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Main table for therapy document chunks
CREATE TABLE IF NOT EXISTS therapy_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector index for cosine similarity search
CREATE INDEX IF NOT EXISTS therapy_chunks_embedding_idx
ON therapy_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- RPC function for similarity search
CREATE OR REPLACE FUNCTION match_therapy_chunks(
    query_embedding vector(384),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        therapy_chunks.id,
        therapy_chunks.content,
        therapy_chunks.metadata,
        1 - (therapy_chunks.embedding <=> query_embedding) AS similarity
    FROM therapy_chunks
    WHERE 1 - (therapy_chunks.embedding <=> query_embedding) >= match_threshold
    ORDER BY therapy_chunks.embedding <=> query_embedding
    LIMIT match_count;
$$;
