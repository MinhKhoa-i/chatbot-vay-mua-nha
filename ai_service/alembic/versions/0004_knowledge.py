"""Create verified-source knowledge ingestion tables."""

from alembic import op

revision = "0004_knowledge"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("""
    CREATE TABLE background_jobs (
      id uuid PRIMARY KEY,
      kind text NOT NULL,
      payload jsonb NOT NULL DEFAULT '{}'::jsonb,
      status text NOT NULL CHECK(status IN ('pending','running','done','dead')),
      run_after timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE knowledge_documents (
      id uuid PRIMARY KEY,
      logical_document_id uuid NOT NULL,
      source_url text,
      title varchar(500) NOT NULL,
      bank_code varchar(50),
      product_type varchar(100),
      original_filename varchar(255) NOT NULL,
      media_type varchar(100) NOT NULL,
      size_bytes bigint NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 20971520),
      content_sha256 char(64) NOT NULL,
      snapshot_path text NOT NULL,
      effective_from date,
      effective_to date,
      last_updated date,
      retrieved_at timestamptz,
      uploaded_at timestamptz NOT NULL DEFAULT now(),
      uploaded_by varchar(200) NOT NULL,
      review_status text NOT NULL CHECK (review_status = 'approved'),
      reviewed_by varchar(200) NOT NULL,
      reviewed_at timestamptz NOT NULL,
      ingestion_status text NOT NULL CHECK (ingestion_status IN ('queued','processing','published','failed')),
      version_no integer NOT NULL CHECK (version_no > 0),
      error_code varchar(100),
      UNIQUE (logical_document_id, version_no),
      UNIQUE (logical_document_id, content_sha256),
      CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from),
      CHECK (source_url IS NULL OR source_url ~* '^https?://[^[:space:]]+$')
    );
    CREATE INDEX ix_knowledge_documents_ingestion ON knowledge_documents(ingestion_status);
    CREATE INDEX ix_knowledge_documents_logical ON knowledge_documents(logical_document_id);

    CREATE TABLE knowledge_chunks (
      id uuid PRIMARY KEY,
      document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
      ordinal integer NOT NULL CHECK (ordinal >= 0),
      body text NOT NULL,
      embedding vector(1536) NOT NULL,
      embedding_model varchar(200) NOT NULL,
      embedding_version varchar(100) NOT NULL CHECK (embedding_version = 'mrl-prefix-1536-l2-v1'),
      textsearch tsvector NOT NULL,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      body_sha256 char(64) NOT NULL,
      UNIQUE(document_id, ordinal)
    );
    CREATE INDEX ix_knowledge_chunks_document ON knowledge_chunks(document_id);
    CREATE INDEX ix_knowledge_chunks_search_gin ON knowledge_chunks USING gin(textsearch);
    CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
      WITH (m = 16, ef_construction = 64);

    CREATE TABLE knowledge_upload_requests (
      operator_ref varchar(200) NOT NULL,
      idempotency_key varchar(200) NOT NULL,
      request_fingerprint char(64) NOT NULL,
      document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
      created_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY(operator_ref, idempotency_key)
    );

    CREATE TABLE ingestion_runs (
      id uuid PRIMARY KEY,
      document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
      status text NOT NULL CHECK (status IN ('processing','published','failed')),
      sha256 char(64) NOT NULL,
      started_at timestamptz NOT NULL,
      finished_at timestamptz,
      error_code varchar(100)
    );
    CREATE INDEX ix_ingestion_runs_document ON ingestion_runs(document_id, started_at DESC);

    CREATE TABLE source_reviews (
      id uuid PRIMARY KEY,
      document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
      reviewer_ref varchar(200) NOT NULL,
      decision text NOT NULL CHECK (decision = 'approved'),
      notes text,
      reviewed_at timestamptz NOT NULL
    );
    """)


def downgrade() -> None:
    op.execute("""
      DROP TABLE IF EXISTS source_reviews;
      DROP TABLE IF EXISTS ingestion_runs;
      DROP TABLE IF EXISTS knowledge_upload_requests;
      DROP TABLE IF EXISTS knowledge_chunks;
      DROP TABLE IF EXISTS knowledge_documents;
      DROP TABLE IF EXISTS background_jobs;
    """)
