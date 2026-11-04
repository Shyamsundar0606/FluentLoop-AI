"""Add persistent interactive learning sessions and progress.

Revision ID: 20261102_0004
Revises: 20261101_0003
Create Date: 2026-11-02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261102_0004"
down_revision = "20261101_0003"
branch_labels = None
depends_on = None

JSON_DOCUMENT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("lessons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("lesson_content_version", sa.String(length=32), nullable=False),
        sa.Column("cefr_level", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("preview_mode", sa.Boolean(), nullable=False),
        sa.Column("lesson_snapshot", JSON_DOCUMENT, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("current_section_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_exercise_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_exercises", sa.Integer(), nullable=False),
        sa.Column("score_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_score_points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_learning_sessions_status",
        ),
        sa.CheckConstraint(
            "cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="ck_learning_sessions_level",
        ),
        sa.CheckConstraint(
            "current_section_position >= 0 AND current_exercise_position >= 0 AND total_exercises >= 0",
            name="ck_learning_sessions_positions",
        ),
        sa.CheckConstraint(
            "score_points >= 0 AND max_score_points >= 0 AND score_points <= max_score_points",
            name="ck_learning_sessions_score",
        ),
    )
    op.create_index(
        "ix_learning_sessions_user_status", "learning_sessions", ["user_id", "status"]
    )
    op.create_index(
        "ix_learning_sessions_user_lesson", "learning_sessions", ["user_id", "lesson_id"]
    )
    op.create_index(
        "ix_learning_sessions_last_activity", "learning_sessions", ["last_activity_at"]
    )
    op.create_index(
        "uq_learning_sessions_active_user_lesson",
        "learning_sessions",
        ["user_id", "lesson_id"],
        unique=True,
        postgresql_where=sa.text("status = 'in_progress'"),
        sqlite_where=sa.text("status = 'in_progress'"),
    )

    op.create_table(
        "learning_session_exercises",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "learning_session_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("learning_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_exercise_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("exercises.id", ondelete="SET NULL"),
        ),
        sa.Column("exercise_order", sa.Integer(), nullable=False),
        sa.Column("exercise_content_version", sa.String(length=32), nullable=False),
        sa.Column("exercise_snapshot", JSON_DOCUMENT, nullable=False),
        sa.Column("max_points", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "learning_session_id", "exercise_order", name="uq_session_exercises_order"
        ),
        sa.UniqueConstraint(
            "learning_session_id", "source_exercise_id", name="uq_session_exercises_source"
        ),
        sa.CheckConstraint(
            "exercise_order > 0 AND max_points >= 0",
            name="ck_session_exercise_score",
        ),
    )
    op.create_index(
        "ix_session_exercises_session",
        "learning_session_exercises",
        ["learning_session_id"],
    )

    op.create_table(
        "exercise_attempts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "learning_session_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("learning_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_exercise_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("learning_session_exercises.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("submitted_answer", sa.String(length=36), nullable=False),
        sa.Column("normalized_answer", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("awarded_points", sa.Integer(), nullable=False),
        sa.Column("max_points", sa.Integer(), nullable=False),
        sa.Column("feedback", JSON_DOCUMENT, nullable=False),
        sa.Column("grading_version", sa.String(length=32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("session_exercise_id", name="uq_attempt_session_exercise"),
        sa.UniqueConstraint(
            "learning_session_id", "idempotency_key", name="uq_attempt_idempotency_key"
        ),
        sa.CheckConstraint("attempt_number > 0", name="ck_attempt_number"),
        sa.CheckConstraint(
            "awarded_points >= 0 AND max_points >= 0",
            name="ck_attempt_points",
        ),
    )
    op.create_index("ix_attempts_user_submitted", "exercise_attempts", ["user_id", "submitted_at"])
    op.create_index("ix_attempts_session", "exercise_attempts", ["learning_session_id"])

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("lessons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("cefr_level", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="not_started"),
        sa.Column("first_started_at", sa.DateTime(timezone=True)),
        sa.Column("last_studied_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("best_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("latest_score", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("completion_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
        sa.CheckConstraint(
            "cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="ck_lesson_progress_level",
        ),
        sa.CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_lesson_progress_status",
        ),
        sa.CheckConstraint("best_score >= 0 AND best_score <= 100", name="ck_lesson_progress_best"),
        sa.CheckConstraint(
            "latest_score >= 0 AND latest_score <= 100",
            name="ck_lesson_progress_latest",
        ),
        sa.CheckConstraint("completion_count >= 0", name="ck_lesson_progress_count"),
    )
    op.create_index(
        "ix_lesson_progress_user_level", "lesson_progress", ["user_id", "cefr_level"]
    )
    op.create_index(
        "ix_lesson_progress_user_lesson", "lesson_progress", ["user_id", "lesson_id"]
    )

    op.create_table(
        "learning_activity_events",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("learning_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "lesson_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("lessons.id", ondelete="SET NULL"),
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_metadata", JSON_DOCUMENT, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_learning_events_user_created",
        "learning_activity_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_learning_events_session", "learning_activity_events", ["session_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_learning_events_session", table_name="learning_activity_events")
    op.drop_index("ix_learning_events_user_created", table_name="learning_activity_events")
    op.drop_table("learning_activity_events")
    op.drop_index("ix_lesson_progress_user_lesson", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_user_level", table_name="lesson_progress")
    op.drop_table("lesson_progress")
    op.drop_index("ix_attempts_session", table_name="exercise_attempts")
    op.drop_index("ix_attempts_user_submitted", table_name="exercise_attempts")
    op.drop_table("exercise_attempts")
    op.drop_index("ix_session_exercises_session", table_name="learning_session_exercises")
    op.drop_table("learning_session_exercises")
    op.drop_index("uq_learning_sessions_active_user_lesson", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_last_activity", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_user_lesson", table_name="learning_sessions")
    op.drop_index("ix_learning_sessions_user_status", table_name="learning_sessions")
    op.drop_table("learning_sessions")
