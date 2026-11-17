"""Explicit ordered lesson prerequisites."""
from alembic import op
import sqlalchemy as sa

revision = "20261115_0014"
down_revision = "20261115_0013"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("lesson_prerequisites",
        sa.Column("lesson_id", sa.Uuid(), sa.ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("prerequisite_id", sa.Uuid(), sa.ForeignKey("lessons.id", ondelete="RESTRICT"), primary_key=True),
        sa.CheckConstraint("lesson_id <> prerequisite_id", name="ck_prerequisite_not_self"))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM lesson_prerequisites)")).scalar_one():
        raise RuntimeError("Downgrade would discard authored lesson prerequisites.")
    op.drop_table("lesson_prerequisites")
