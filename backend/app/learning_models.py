from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


STRUCTURED_JSON = JSON().with_variant(JSONB, "postgresql")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'abandoned')",
            name="ck_learning_sessions_status",
        ),
        CheckConstraint(
            "cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="ck_learning_sessions_level",
        ),
        CheckConstraint(
            "current_section_position >= 0 AND current_exercise_position >= 0 AND total_exercises >= 0",
            name="ck_learning_sessions_positions",
        ),
        CheckConstraint(
            "score_points >= 0 AND max_score_points >= 0 AND score_points <= max_score_points",
            name="ck_learning_sessions_score",
        ),
        Index("ix_learning_sessions_user_status", "user_id", "status"),
        Index("ix_learning_sessions_user_lesson", "user_id", "lesson_id"),
        Index("ix_learning_sessions_last_activity", "last_activity_at"),
        Index(
            "uq_learning_sessions_active_user_lesson",
            "user_id",
            "lesson_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
            sqlite_where=text("status = 'in_progress'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False
    )
    lesson_content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="in_progress")
    preview_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lesson_snapshot: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    current_section_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_exercise_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_exercises: Mapped[int] = mapped_column(Integer, nullable=False)
    score_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_score_points: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class LearningSessionExercise(Base):
    __tablename__ = "learning_session_exercises"
    __table_args__ = (
        UniqueConstraint(
            "learning_session_id", "exercise_order", name="uq_session_exercises_order"
        ),
        UniqueConstraint(
            "learning_session_id", "source_exercise_id", name="uq_session_exercises_source"
        ),
        CheckConstraint("exercise_order > 0 AND max_points >= 0", name="ck_session_exercise_score"),
        Index("ix_session_exercises_session", "learning_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    learning_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_exercise_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exercises.id", ondelete="SET NULL")
    )
    exercise_order: Mapped[int] = mapped_column(Integer, nullable=False)
    exercise_content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    exercise_snapshot: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False)
    max_points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"
    __table_args__ = (
        UniqueConstraint("session_exercise_id", name="uq_attempt_session_exercise"),
        UniqueConstraint(
            "learning_session_id", "idempotency_key", name="uq_attempt_idempotency_key"
        ),
        CheckConstraint("attempt_number > 0", name="ck_attempt_number"),
        CheckConstraint("awarded_points >= 0 AND max_points >= 0", name="ck_attempt_points"),
        Index("ix_attempts_user_submitted", "user_id", "submitted_at"),
        Index("ix_attempts_session", "learning_session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    learning_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="CASCADE"), nullable=False
    )
    session_exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_session_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    submitted_answer: Mapped[str] = mapped_column(String(36), nullable=False)
    normalized_answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    awarded_points: Mapped[int] = mapped_column(Integer, nullable=False)
    max_points: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False)
    grading_version: Mapped[str] = mapped_column(String(32), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
        CheckConstraint(
            "cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="ck_lesson_progress_level",
        ),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_lesson_progress_status",
        ),
        CheckConstraint("best_score >= 0 AND best_score <= 100", name="ck_lesson_progress_best"),
        CheckConstraint("latest_score >= 0 AND latest_score <= 100", name="ck_lesson_progress_latest"),
        CheckConstraint("completion_count >= 0", name="ck_lesson_progress_count"),
        Index("ix_lesson_progress_user_level", "user_id", "cefr_level"),
        Index("ix_lesson_progress_user_lesson", "user_id", "lesson_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False
    )
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="not_started")
    first_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_studied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    best_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    latest_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    completion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class LearningActivityEvent(Base):
    __tablename__ = "learning_activity_events"
    __table_args__ = (
        Index("ix_learning_events_user_created", "user_id", "created_at"),
        Index("ix_learning_events_session", "session_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("learning_sessions.id", ondelete="SET NULL")
    )
    lesson_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_metadata: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
