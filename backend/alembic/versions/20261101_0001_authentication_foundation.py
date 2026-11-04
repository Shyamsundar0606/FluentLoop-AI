"""Add user identity, preferences, sessions, and one-time auth tokens.

Revision ID: 20261101_0001
Revises:
Create Date: 2026-11-01
"""

from alembic import op
import sqlalchemy as sa

revision = "20261101_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="learner"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('learner', 'admin')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("preferred_name", sa.String(length=80), nullable=True),
        sa.Column("native_language", sa.String(length=32), nullable=False, server_default="English"),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("learning_goal", sa.String(length=80), nullable=True),
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("explanation_language", sa.String(length=32), nullable=False, server_default="English"),
        sa.Column("target_language", sa.String(length=32), nullable=False, server_default="French"),
        sa.Column("current_level", sa.String(length=16), nullable=False, server_default="pre_a1"),
        sa.Column("target_level", sa.String(length=16), nullable=True),
        sa.Column("daily_study_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("learning_focus", sa.String(length=16), nullable=False, server_default="balanced"),
        sa.Column("theme", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("audio_playback_speed", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("explanation_language IN ('English')", name="ck_user_preferences_explanation_language"),
        sa.CheckConstraint("target_language IN ('French')", name="ck_user_preferences_target_language"),
        sa.CheckConstraint("current_level IN ('pre_a1', 'a1', 'a2', 'b1', 'b2', 'c1', 'c2')", name="ck_user_preferences_current_level"),
        sa.CheckConstraint("target_level IS NULL OR target_level IN ('pre_a1', 'a1', 'a2', 'b1', 'b2', 'c1', 'c2')", name="ck_user_preferences_target_level"),
        sa.CheckConstraint("daily_study_minutes IN (5, 10, 15, 20, 30)", name="ck_user_preferences_study_minutes"),
        sa.CheckConstraint("learning_focus IN ('speaking', 'listening', 'reading', 'writing', 'balanced')", name="ck_user_preferences_learning_focus"),
        sa.CheckConstraint("theme IN ('light', 'dark', 'system')", name="ck_user_preferences_theme"),
        sa.CheckConstraint("audio_playback_speed >= 0.5 AND audio_playback_speed <= 2.0", name="ck_user_preferences_audio_speed"),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=256), nullable=True),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])

    for table in ("email_verification_tokens", "password_reset_tokens"):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])
        op.create_index(f"ix_{table}_expires_at", table, ["expires_at"])


def downgrade() -> None:
    for table in ("password_reset_tokens", "email_verification_tokens", "user_sessions", "user_preferences", "user_profiles", "users"):
        op.drop_table(table)
