"""Restrict French levels to CEFR A1-C2 and migrate legacy values.

Revision ID: 20261101_0002
Revises: 20261101_0001
Create Date: 2026-11-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20261101_0002"
down_revision = "20261101_0001"
branch_labels = None
depends_on = None

LEVELS = "'a1', 'a2', 'b1', 'b2', 'c1', 'c2'"


def upgrade() -> None:
    op.drop_constraint("ck_user_preferences_current_level", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_target_level", "user_preferences", type_="check")

    op.execute(
        sa.text(
            "UPDATE user_preferences SET current_level = 'a1' "
            "WHERE current_level = 'pre_a1'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE user_preferences SET target_level = 'a1' "
            "WHERE target_level = 'pre_a1'"
        )
    )
    op.alter_column(
        "user_preferences",
        "current_level",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        server_default="a1",
    )
    op.create_check_constraint(
        "ck_user_preferences_current_level",
        "user_preferences",
        f"current_level IN ({LEVELS})",
    )
    op.create_check_constraint(
        "ck_user_preferences_target_level",
        "user_preferences",
        f"target_level IS NULL OR target_level IN ({LEVELS})",
    )


def downgrade() -> None:
    op.drop_constraint("ck_user_preferences_current_level", "user_preferences", type_="check")
    op.drop_constraint("ck_user_preferences_target_level", "user_preferences", type_="check")
    op.alter_column(
        "user_preferences",
        "current_level",
        existing_type=sa.String(length=16),
        existing_nullable=False,
        server_default="pre_a1",
    )
    op.create_check_constraint(
        "ck_user_preferences_current_level",
        "user_preferences",
        "current_level IN ('pre_a1', 'a1', 'a2', 'b1', 'b2', 'c1', 'c2')",
    )
    op.create_check_constraint(
        "ck_user_preferences_target_level",
        "user_preferences",
        "target_level IS NULL OR target_level IN ('pre_a1', 'a1', 'a2', 'b1', 'b2', 'c1', 'c2')",
    )
