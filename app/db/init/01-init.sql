CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    doc_id UUID PRIMARY KEY,
    payload JSONB,
    embedding vector(3072),
    created_at TIMESTAMP DEFAULT NOW()
);

-- -- Create index on embedding column using HNSW
-- CREATE INDEX chunk_embedding_idx ON embeddings
-- USING hnsw (embedding halfvec_cosine_ops);   