"""Milestone 06: additive speech metadata; private audio lives outside PostgreSQL."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261102_0007"
down_revision = "20261102_0006"
branch_labels = None
depends_on = None
JSON_DOCUMENT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade():
    op.create_table(
        "speech_sessions",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ai_conversation_id",
            sa.Uuid(),
            sa.ForeignKey("ai_conversations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cefr_level", sa.String(2), nullable=False),
        sa.Column("scenario_id", sa.String(80), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active_request_id", sa.Uuid(), nullable=True),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "cefr_level IN ('A1','A2','B1','B2','C1','C2')", name="ck_speech_level"
        ),
        sa.CheckConstraint("status IN ('active','completed')", name="ck_speech_status"),
        sa.UniqueConstraint("ai_conversation_id", name=None),
    )
    op.create_index(
        "ix_speech_owner_activity",
        "speech_sessions",
        ["user_id", "last_activity_at"],
        unique=False,
    )
    op.create_table(
        "speech_audio_assets",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "speech_session_id",
            sa.Uuid(),
            sa.ForeignKey("speech_sessions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "lesson_id",
            sa.Uuid(),
            sa.ForeignKey("lessons.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("content_version", sa.String(32), nullable=True),
        sa.Column("storage_key", sa.String(80), nullable=False),
        sa.Column("media_type", sa.String(80), nullable=False),
        sa.Column("codec", sa.String(32), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("storage_key", name=None),
    )
    op.create_index(
        "ix_speech_audio_assets_owner_user_id",
        "speech_audio_assets",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_speech_audio_assets_retention_expires_at",
        "speech_audio_assets",
        ["retention_expires_at"],
        unique=False,
    )
    op.create_table(
        "speech_turns",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "speech_session_id",
            sa.Uuid(),
            sa.ForeignKey("speech_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("input_checksum", sa.String(64), nullable=False),
        sa.Column(
            "ai_message_id",
            sa.Uuid(),
            sa.ForeignKey("ai_messages.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("asr_model", sa.String(120), nullable=True),
        sa.Column("transcription_status", sa.String(24), nullable=False),
        sa.Column("transcription_metadata", JSON_DOCUMENT, nullable=False),
        sa.Column(
            "audio_asset_id",
            sa.Uuid(),
            sa.ForeignKey("speech_audio_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tutor_audio_asset_id",
            sa.Uuid(),
            sa.ForeignKey("speech_audio_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("spoken_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "speech_session_id", "request_id", name="uq_speech_turn_request"
        ),
        sa.CheckConstraint(
            "status IN ('pending','success','failed','unusable')",
            name="ck_speech_turn_status",
        ),
    )
    op.create_index(
        "ix_speech_turn_session_time",
        "speech_turns",
        ["speech_session_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_speech_turns_user_id", "speech_turns", ["user_id"], unique=False
    )
    op.create_table(
        "pronunciation_attempts",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("input_checksum", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=False),
        sa.Column("target_text", sa.Text(), nullable=False),
        sa.Column(
            "lesson_id",
            sa.Uuid(),
            sa.ForeignKey("lessons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content_version", sa.String(32), nullable=False),
        sa.Column("target_level", sa.String(2), nullable=False),
        sa.Column("recognized_text", sa.Text(), nullable=False),
        sa.Column("recognition_match", sa.Boolean(), nullable=True),
        sa.Column("assessment_status", sa.String(24), nullable=False),
        sa.Column("acoustic_score", sa.Integer(), nullable=True),
        sa.Column("assessor_model", sa.String(120), nullable=True),
        sa.Column("assessor_version", sa.String(40), nullable=True),
        sa.Column("feedback_metadata", JSON_DOCUMENT, nullable=False),
        sa.Column(
            "audio_asset_id",
            sa.Uuid(),
            sa.ForeignKey("speech_audio_assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "acoustic_score IS NULL", name="ck_no_unvalidated_acoustic_score"
        ),
        sa.CheckConstraint(
            "assessment_status IN ('not_available','insufficient_audio')",
            name="ck_pronunciation_assessment",
        ),
        sa.UniqueConstraint("user_id", "request_id", name="uq_pronunciation_request"),
    )
    op.create_index(
        "ix_pronunciation_attempts_user_id",
        "pronunciation_attempts",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "speech_practice_progress",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_id", sa.String(100), nullable=False),
        sa.Column(
            "lesson_id",
            sa.Uuid(),
            sa.ForeignKey("lessons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("content_version", sa.String(32), nullable=False),
        sa.Column("cefr_level", sa.String(2), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_practiced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_assessment_status", sa.String(24), nullable=False),
        sa.Column("latest_validated_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "target_id", name="uq_speech_progress_target"),
        sa.CheckConstraint(
            "latest_validated_score IS NULL", name="ck_no_unvalidated_progress_score"
        ),
    )
    op.create_index(
        "ix_speech_practice_progress_user_id",
        "speech_practice_progress",
        ["user_id"],
        unique=False,
    )


def downgrade():
    op.drop_table("speech_practice_progress")
    op.drop_table("pronunciation_attempts")
    op.drop_table("speech_turns")
    op.drop_table("speech_audio_assets")
    op.drop_table("speech_sessions")
