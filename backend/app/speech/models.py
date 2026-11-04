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


class SpeechSession(Base):
    __tablename__ = "speech_sessions"
    __table_args__ = (
        CheckConstraint(
            "cefr_level IN ('A1','A2','B1','B2','C1','C2')", name="ck_speech_level"
        ),
        CheckConstraint("status IN ('active','completed')", name="ck_speech_status"),
        Index("ix_speech_owner_activity", "user_id", "last_activity_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ai_conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ai_conversations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    active_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class AudioAsset(Base):
    __tablename__ = "speech_audio_assets"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    speech_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("speech_sessions.id", ondelete="CASCADE")
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="RESTRICT")
    )
    content_version: Mapped[str | None] = mapped_column(String(32))
    storage_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    media_type: Mapped[str] = mapped_column(String(80), nullable=False)
    codec: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    retention_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SpeechTurn(Base):
    __tablename__ = "speech_turns"
    __table_args__ = (
        UniqueConstraint(
            "speech_session_id", "request_id", name="uq_speech_turn_request"
        ),
        CheckConstraint(
            "status IN ('pending','success','failed','unusable')",
            name="ck_speech_turn_status",
        ),
        Index("ix_speech_turn_session_time", "speech_session_id", "created_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    speech_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("speech_sessions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    ai_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("ai_messages.id", ondelete="RESTRICT")
    )
    transcript: Mapped[str] = mapped_column(Text, default="", nullable=False)
    language: Mapped[str | None] = mapped_column(String(10))
    asr_model: Mapped[str | None] = mapped_column(String(120))
    transcription_status: Mapped[str] = mapped_column(
        String(24), default="pending", nullable=False
    )
    transcription_metadata: Mapped[dict] = mapped_column(
        STRUCTURED_JSON, default=dict, nullable=False
    )
    audio_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("speech_audio_assets.id", ondelete="SET NULL")
    )
    tutor_audio_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("speech_audio_assets.id", ondelete="SET NULL")
    )
    spoken_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class PronunciationAttempt(Base):
    __tablename__ = "pronunciation_attempts"
    __table_args__ = (
        UniqueConstraint("user_id", "request_id", name="uq_pronunciation_request"),
        CheckConstraint(
            "acoustic_score IS NULL", name="ck_no_unvalidated_acoustic_score"
        ),
        CheckConstraint(
            "assessment_status IN ('not_available','insufficient_audio')",
            name="ck_pronunciation_assessment",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    input_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    target_text: Mapped[str] = mapped_column(Text, nullable=False)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False
    )
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    target_level: Mapped[str] = mapped_column(String(2), nullable=False)
    recognized_text: Mapped[str] = mapped_column(Text, nullable=False)
    recognition_match: Mapped[bool | None] = mapped_column(Boolean)
    assessment_status: Mapped[str] = mapped_column(String(24), nullable=False)
    acoustic_score: Mapped[int | None] = mapped_column(Integer)
    assessor_model: Mapped[str | None] = mapped_column(String(120))
    assessor_version: Mapped[str | None] = mapped_column(String(40))
    feedback_metadata: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False)
    audio_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("speech_audio_assets.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class SpeechProgress(Base):
    __tablename__ = "speech_practice_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "target_id", name="uq_speech_progress_target"),
        CheckConstraint(
            "latest_validated_score IS NULL", name="ck_no_unvalidated_progress_score"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_id: Mapped[str] = mapped_column(String(100), nullable=False)
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="RESTRICT"), nullable=False
    )
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_practiced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    latest_assessment_status: Mapped[str] = mapped_column(String(24), nullable=False)
    latest_validated_score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
