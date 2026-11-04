import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.curriculum_models import STRUCTURED_JSON
from app.models import utcnow


class Conversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        CheckConstraint(
            "cefr_level IN ('A1','A2','B1','B2','C1','C2')", name="ck_ai_level"
        ),
        CheckConstraint(
            "mode IN ('tutor','vocabulary','grammar','correction','roleplay')",
            name="ck_ai_mode",
        ),
        CheckConstraint("status IN ('active','archived')", name="ck_ai_status"),
        Index("ix_ai_owner_updated", "user_id", "updated_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(String(80))
    linked_lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    model_provider: Mapped[str] = mapped_column(
        String(32), default="ollama", nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    preview_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_version_reference: Mapped[str | None] = mapped_column(String(32))
    active_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    generation_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class Message(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')", name="ck_ai_message_role"),
        CheckConstraint(
            "response_status IN ('pending','success','failed')",
            name="ck_ai_message_status",
        ),
        CheckConstraint(
            "grounding_status IN ('general_knowledge','curriculum_context','draft_preview','unverified')",
            name="ck_ai_grounding",
        ),
        UniqueConstraint(
            "conversation_id", "request_id", "role", name="uq_ai_turn_request_role"
        ),
        Index("ix_ai_messages_conversation_created", "conversation_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(String(120))
    response_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    grounding_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="unverified"
    )
    model_metadata: Mapped[dict] = mapped_column(
        STRUCTURED_JSON, default=dict, nullable=False
    )
    request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class MessageSource(Base):
    __tablename__ = "ai_message_sources"
    __table_args__ = (
        UniqueConstraint("message_id", "source_record_id", name="uq_ai_message_source"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(
        String(24), nullable=False, default="lesson"
    )
    source_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False
    )
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    retrieval_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class PracticeFeedback(Base):
    __tablename__ = "ai_practice_feedback"
    __table_args__ = (UniqueConstraint("message_id", name="uq_ai_feedback_message"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ai_messages.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    corrected_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Recommendation(Base):
    __tablename__ = "ai_learning_recommendations"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "cefr_level", "topic", name="uq_ai_recommendation_topic"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    linked_lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    source_activity_reference: Mapped[dict] = mapped_column(
        STRUCTURED_JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
