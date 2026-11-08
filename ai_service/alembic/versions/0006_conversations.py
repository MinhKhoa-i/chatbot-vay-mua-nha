"""Create encrypted conversation persistence tables.

Revision ID: 0006_conversations
Revises: 0005_jobs_ops
"""

from alembic import op

revision = "0006_conversations"
down_revision = "0005_jobs_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE conversations (
      id uuid PRIMARY KEY,
      status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed','deleted')),
      checkpoint_ciphertext bytea,
      version bigint NOT NULL DEFAULT 0 CHECK (version >= 0),
      active_request_id uuid,
      last_active_at timestamptz NOT NULL DEFAULT now(),
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      expires_at timestamptz NOT NULL,
      deleted_at timestamptz,
      CHECK (
        (status IN ('active','closed') AND checkpoint_ciphertext IS NOT NULL AND deleted_at IS NULL)
        OR (status='deleted' AND checkpoint_ciphertext IS NULL AND deleted_at IS NOT NULL AND active_request_id IS NULL)
      ),
      CHECK (expires_at > last_active_at)
    );
    CREATE INDEX ix_conversations_expiry ON conversations(expires_at) WHERE status <> 'deleted';

    CREATE TABLE conversation_profiles (
      conversation_id uuid PRIMARY KEY REFERENCES conversations(id) ON DELETE CASCADE,
      slots_ciphertext bytea NOT NULL,
      revision bigint NOT NULL DEFAULT 0 CHECK (revision >= 0),
      updated_at timestamptz NOT NULL DEFAULT now()
    );

    CREATE TABLE messages (
      id uuid PRIMARY KEY,
      conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
      role text NOT NULL CHECK (role IN ('user','assistant','system')),
      content_ciphertext bytea NOT NULL,
      metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
      seq bigint NOT NULL CHECK (seq > 0),
      created_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (conversation_id, seq)
    );
    CREATE INDEX ix_messages_conversation_seq ON messages(conversation_id, seq DESC);

    CREATE TABLE message_requests (
      id uuid PRIMARY KEY,
      conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
      client_request_id uuid NOT NULL,
      operation text NOT NULL CHECK (operation IN ('send_message','patch_profile','confirm_profile','calculate_loan','recommend_banks')),
      request_hash char(64) NOT NULL,
      status text NOT NULL CHECK (status IN ('processing','completed','failed')),
      snapshot_version bigint NOT NULL CHECK (snapshot_version >= 0),
      lease_token uuid,
      lease_expires_at timestamptz,
      attempts integer NOT NULL DEFAULT 1,
      max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts > 0),
      retryable boolean NOT NULL DEFAULT false,
      next_retry_at timestamptz,
      response_ciphertext bytea,
      response_status integer CHECK (response_status BETWEEN 200 AND 599),
      error_code text,
      created_at timestamptz NOT NULL DEFAULT now(),
      updated_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE (conversation_id, client_request_id),
      CHECK (attempts BETWEEN 1 AND max_attempts),
      CHECK (
        (status='processing' AND lease_token IS NOT NULL AND lease_expires_at IS NOT NULL)
        OR (status<>'processing' AND lease_token IS NULL AND lease_expires_at IS NULL)
      ),
      CHECK (status<>'completed' OR (response_ciphertext IS NOT NULL AND response_status BETWEEN 200 AND 299 AND error_code IS NULL AND retryable=false)),
      CHECK (status<>'failed' OR (error_code IS NOT NULL AND response_ciphertext IS NOT NULL AND response_status BETWEEN 400 AND 599)),
      CHECK (retryable=false OR (status='failed' AND attempts < max_attempts))
    );
    CREATE UNIQUE INDEX uq_requests_one_processing ON message_requests(conversation_id) WHERE status='processing';
    CREATE INDEX ix_requests_lease ON message_requests(lease_expires_at) WHERE status='processing';
    """)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS message_requests;
    DROP TABLE IF EXISTS messages;
    DROP TABLE IF EXISTS conversation_profiles;
    DROP TABLE IF EXISTS conversations;
    """)
