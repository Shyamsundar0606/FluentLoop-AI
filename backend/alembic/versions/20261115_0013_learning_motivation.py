"""Idempotent activity rewards and optional learning motivation."""
from alembic import op
import sqlalchemy as sa

revision = "20261115_0013"
down_revision = "20261115_0012"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_preferences", sa.Column("motivation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("learning_rewards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", sa.String(128), nullable=False),
        sa.Column("xp", sa.Integer(), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("study_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False),
        sa.UniqueConstraint("user_id", "kind", "source_id", name="uq_reward_source"),
        sa.CheckConstraint("xp > 0", name="ck_reward_positive"))
    op.create_index("ix_reward_owner_date", "learning_rewards", ["user_id", "study_date"])
    op.create_table("learning_achievements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("achievement_key", sa.String(80), nullable=False),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "achievement_key", name="uq_achievement_owner"))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM learning_rewards) OR EXISTS "
        "(SELECT 1 FROM learning_achievements) OR EXISTS (SELECT 1 FROM user_preferences WHERE NOT motivation_enabled)")).scalar_one():
        raise RuntimeError("Downgrade would discard rewards, achievements or motivation preferences.")
    op.drop_table("learning_achievements")
    op.drop_index("ix_reward_owner_date", table_name="learning_rewards")
    op.drop_table("learning_rewards")
    op.drop_column("user_preferences", "motivation_enabled")
