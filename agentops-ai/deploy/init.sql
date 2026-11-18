CREATE EXTENSION IF NOT EXISTS vector;

-- SQLAlchemy creates the application tables. This optional table is the
-- retrieval extension point for curated runbooks or resolved-incident snippets.
-- Keep embeddings permission-filtered and do not store raw sensitive logs here.
CREATE TABLE IF NOT EXISTS incident_knowledge (
  id bigserial PRIMARY KEY,
  tenant_id text NOT NULL,
  pipeline text NOT NULL,
  source_ref text NOT NULL,
  body text NOT NULL,
  embedding vector(1536),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS incident_knowledge_embedding_idx
  ON incident_knowledge USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS incident_knowledge_scope_idx
  ON incident_knowledge (tenant_id, pipeline);
