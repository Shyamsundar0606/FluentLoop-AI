"""Milestone 07 records; no updates to pre-existing learning tables."""
import uuid
from datetime import date, datetime
from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey,
    ForeignKeyConstraint, Index, Integer, String, Text, UniqueConstraint, Uuid, text)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.curriculum_models import STRUCTURED_JSON
from app.models import utcnow

LEVELS = "cefr_level IN ('A1','A2','B1','B2','C1','C2')"

class Record:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class DailyPlan(Record, Base):
    __tablename__ = "daily_learning_plans"
    __table_args__ = (
        UniqueConstraint("user_id", "local_study_date", "cefr_level", name="uq_daily_plan_identity"),
        UniqueConstraint("id", "user_id", name="uq_daily_plan_owner"),
        CheckConstraint(LEVELS, name="ck_daily_plan_level"),
        CheckConstraint("status IN ('ready','in_progress','completed')", name="ck_daily_plan_status"),
        CheckConstraint("target_minutes IN (5,10,15,20,30) AND generation > 0", name="ck_daily_plan_target"),
        Index("ix_daily_plan_owner_date", "user_id", "local_study_date"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    local_study_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(64), nullable=False)
    target_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ready", nullable=False)
    plan_version: Mapped[str] = mapped_column(String(32), default="priority-v1", nullable=False)
    generation: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    generation_request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    generation_was_regeneration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class ReviewCard(Record, Base):
    __tablename__ = "spaced_repetition_cards"
    __table_args__ = (
        UniqueConstraint("user_id", "word_sense_id", "cefr_level", "card_type", name="uq_review_card_identity"),
        UniqueConstraint("id", "user_id", name="uq_review_card_owner"),
        CheckConstraint(LEVELS, name="ck_review_card_level"),
        CheckConstraint("state IN ('new','learning','review','relearning')", name="ck_review_card_state"),
        CheckConstraint("card_type = 'english_to_french'", name="ck_review_card_type"),
        CheckConstraint("repetition_count >= 0 AND lapse_count >= 0 AND interval_days >= 0 AND interval_days <= 365 AND ease_factor >= 1.3 AND ease_factor <= 3.0", name="ck_review_card_schedule"),
        Index("ix_review_card_owner_due", "user_id", "cefr_level", "next_due_at"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_sense_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("word_senses.id", ondelete="RESTRICT"), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    card_type: Mapped[str] = mapped_column(String(32), default="english_to_french", nullable=False)
    card_content_version: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    repetition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    interval_days: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    next_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recent_result: Mapped[bool | None] = mapped_column(Boolean)
    lapse_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), default="fl-sm2-v1", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

class ReviewSession(Record, Base):
    __tablename__ = "vocabulary_review_sessions"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_review_session_owner"),
        UniqueConstraint("user_id", "request_id", name="uq_review_session_request"),
        CheckConstraint(LEVELS, name="ck_review_session_level"),
        CheckConstraint("status IN ('active','completed') AND card_limit >= 1 AND card_limit <= 20", name="ck_review_session_status"),
        Index("uq_review_active_owner_level", "user_id", "cefr_level", unique=True,
              postgresql_where=text("status = 'active'"), sqlite_where=text("status = 'active'")),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    card_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ReviewItem(Record, Base):
    __tablename__ = "vocabulary_review_session_items"
    __table_args__ = (
        UniqueConstraint("session_id", "card_id", name="uq_review_session_card"),
        UniqueConstraint("session_id", "sequence_order", name="uq_review_item_order"),
        UniqueConstraint("id", "user_id", name="uq_review_item_owner"),
        UniqueConstraint("id", "session_id", "card_id", "user_id", name="uq_review_item_context"),
        ForeignKeyConstraint(["session_id", "user_id"], ["vocabulary_review_sessions.id", "vocabulary_review_sessions.user_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["card_id", "user_id"], ["spaced_repetition_cards.id", "spaced_repetition_cards.user_id"], ondelete="RESTRICT"),
        CheckConstraint("sequence_order > 0", name="ck_review_item_order"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    card_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    # Private answer snapshot; never serialized before an authorized submission.
    snapshot: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False)

class ReviewAttempt(Record, Base):
    __tablename__ = "spaced_repetition_reviews"
    __table_args__ = (
        UniqueConstraint("session_id", "request_id", name="uq_review_answer_request"),
        UniqueConstraint("item_id", name="uq_review_answer_item"),
        ForeignKeyConstraint(["session_id", "user_id"], ["vocabulary_review_sessions.id", "vocabulary_review_sessions.user_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["item_id", "session_id", "card_id", "user_id"], ["vocabulary_review_session_items.id", "vocabulary_review_session_items.session_id", "vocabulary_review_session_items.card_id", "vocabulary_review_session_items.user_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["card_id", "user_id"], ["spaced_repetition_cards.id", "spaced_repetition_cards.user_id"], ondelete="RESTRICT"),
        CheckConstraint("recall_rating IS NULL OR recall_rating IN ('easy','normal','difficult')", name="ck_review_rating"),
        Index("ix_review_history_owner_time", "user_id", "reviewed_at"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    item_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    card_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    submitted_answer: Mapped[str] = mapped_column(String(300), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recall_rating: Mapped[str | None] = mapped_column(String(16))
    previous_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    new_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_interval_days: Mapped[float] = mapped_column(Float, nullable=False)
    new_interval_days: Mapped[float] = mapped_column(Float, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)
    schedule_before: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False)
    schedule_after: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False)

class DailyActivity(Record, Base):
    __tablename__ = "daily_learning_activities"
    __table_args__ = (
        ForeignKeyConstraint(["plan_id", "user_id"], ["daily_learning_plans.id", "daily_learning_plans.user_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["linked_review_session_id", "user_id"], ["vocabulary_review_sessions.id", "vocabulary_review_sessions.user_id"], ondelete="RESTRICT"),
        UniqueConstraint("plan_id", "generation", "sequence_order", name="uq_plan_activity_order"),
        CheckConstraint("activity_type IN ('vocabulary_review','continue_lesson','lesson_review','new_lesson','tutor','speaking')", name="ck_daily_activity_type"),
        CheckConstraint("status IN ('pending','in_progress','completed','cancelled')", name="ck_daily_activity_status"),
        CheckConstraint("estimated_minutes > 0 AND estimated_minutes <= 15 AND sequence_order > 0 AND generation > 0", name="ck_daily_activity_estimate"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    generation: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    evidence: Mapped[dict] = mapped_column(STRUCTURED_JSON, default=dict, nullable=False)
    linked_lesson_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("lessons.id", ondelete="RESTRICT"))
    linked_learning_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("learning_sessions.id", ondelete="RESTRICT"))
    linked_review_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    linked_conversation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("ai_conversations.id", ondelete="RESTRICT"))
    linked_speech_session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("speech_sessions.id", ondelete="RESTRICT"))
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
