"""Add job retry, lease, and error fields used by the local worker."""

from alembic import op

revision = "0005_jobs_ops"
down_revision = "0004_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
      ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS lease_token uuid;
      ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS lease_until timestamptz;
      ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS idempotency_key text;
      ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS last_error_code text;
      ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS attempts integer NOT NULL DEFAULT 0;
      ALTER TABLE background_jobs ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 5;
      CREATE UNIQUE INDEX IF NOT EXISTS uq_background_jobs_idempotency
        ON background_jobs(idempotency_key);
      CREATE INDEX IF NOT EXISTS ix_background_jobs_next
        ON background_jobs(status, run_after) WHERE status = 'pending';
    """)


def downgrade() -> None:
    op.execute("""
      DROP INDEX IF EXISTS ix_background_jobs_next;
      DROP INDEX IF EXISTS uq_background_jobs_idempotency;
      ALTER TABLE background_jobs DROP COLUMN IF EXISTS last_error_code;
      ALTER TABLE background_jobs DROP COLUMN IF EXISTS idempotency_key;
      ALTER TABLE background_jobs DROP COLUMN IF EXISTS lease_until;
      ALTER TABLE background_jobs DROP COLUMN IF EXISTS lease_token;
      ALTER TABLE background_jobs DROP COLUMN IF EXISTS max_attempts;
      ALTER TABLE background_jobs DROP COLUMN IF EXISTS attempts;
    """)
