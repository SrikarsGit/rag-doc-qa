CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id TEXT UNIQUE,
    payload JSONB,
    embedding vector(3072)
);

-- -- Create index on embedding column using HNSW
-- CREATE INDEX chunk_embedding_idx ON embeddings
-- USING hnsw (embedding halfvec_cosine_ops);   