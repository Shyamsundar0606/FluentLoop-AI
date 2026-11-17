"""Recoverable account audio erasure outbox."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261115_0015"
down_revision = "20261115_0014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("account_erasure_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("storage_keys", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM account_erasure_jobs)")).scalar_one():
        raise RuntimeError("Downgrade would discard account erasure recovery or audit records.")
    op.drop_table("account_erasure_jobs")
