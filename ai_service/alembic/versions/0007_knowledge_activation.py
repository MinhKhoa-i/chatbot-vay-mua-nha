"""Add activation flag to knowledge documents."""

from alembic import op
import sqlalchemy as sa

revision = "0007_knowledge_activation"
down_revision = "0006_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_documents",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )


def downgrade() -> None:
    op.drop_column("knowledge_documents", "is_active")
