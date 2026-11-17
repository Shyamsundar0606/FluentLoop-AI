"""Preserve original writing independently of objective exercise scores."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261115_0011"
down_revision = "20261108_0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("writing_submissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), sa.ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("cefr_level", sa.String(2), nullable=False),
        sa.Column("lesson_content_version", sa.String(32), nullable=False),
        sa.Column("prompt_snapshot", sa.Text(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("preview_mode", sa.Boolean(), nullable=False),
        sa.Column("feedback_status", sa.String(16), nullable=False),
        sa.Column("advisory_feedback", sa.JSON().with_variant(postgresql.JSONB(), "postgresql")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_writing_owner_request"),
        sa.CheckConstraint("cefr_level IN ('A1','A2','B1','B2','C1','C2')", name="ck_writing_level"),
        sa.CheckConstraint("feedback_status IN ('not_requested','available','unavailable')", name="ck_writing_feedback"))
    op.create_index("ix_writing_owner_created", "writing_submissions", ["user_id", "created_at"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM writing_submissions)")).scalar_one():
        raise RuntimeError("Downgrade would discard saved writing submissions. Export and review recovery first.")
    op.drop_index("ix_writing_owner_created", table_name="writing_submissions")
    op.drop_table("writing_submissions")
