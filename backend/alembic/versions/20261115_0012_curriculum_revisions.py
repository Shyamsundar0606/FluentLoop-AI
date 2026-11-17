"""Preserve actual authored curriculum packets for version comparison."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261115_0012"
down_revision = "20261115_0011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("curriculum_revisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("content_version", sa.String(32), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("packet", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("course_id", "digest", name="uq_curriculum_revision_digest"))
    op.create_index("ix_curriculum_revision_course_created", "curriculum_revisions", ["course_id", "created_at"])


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM curriculum_revisions)")).scalar_one():
        raise RuntimeError("Downgrade would discard persisted curriculum versions.")
    op.drop_index("ix_curriculum_revision_course_created", table_name="curriculum_revisions")
    op.drop_table("curriculum_revisions")
