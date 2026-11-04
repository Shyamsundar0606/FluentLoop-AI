from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field
from app.ai.response_schemas import StrictModel, Level, ChatResponse


class Word(StrictModel):
    text: str = Field(max_length=200)
    start: float = Field(ge=0, le=31)
    end: float = Field(ge=0, le=31)


class Segment(StrictModel):
    text: str = Field(max_length=4000)
    start: float = Field(ge=0, le=31)
    end: float = Field(ge=0, le=31)


class Transcription(StrictModel):
    codec: str | None = Field(default=None,max_length=32)
    container: str | None = Field(default=None,max_length=80)
    status: Literal[
        "transcribed", "no_speech", "uncertain", "non_french", "insufficient_audio"
    ]
    language: str | None = Field(default=None, max_length=10)
    detected_language: str | None = Field(default=None, max_length=10)
    language_mode: Literal["detected", "constrained"] = "detected"
    language_detection_probability: float | None = Field(default=None, ge=0, le=1)
    text: str = Field(default="", max_length=4000)
    duration_ms: int = Field(ge=0, le=30000)
    model: str
    segments: list[Segment] = Field(default_factory=list, max_length=100)
    words: list[Word] = Field(default_factory=list, max_length=500)
    audio_quality: list[str] = Field(default_factory=list, max_length=10)
    processing_ms: int | None = Field(default=None, ge=0)


class StartSpeech(StrictModel):
    scenario_id: str | None = Field(default=None, max_length=80)
    conversation_id: UUID | None = None
    level: Level | None = None


class Synthesize(StrictModel):
    text: str = Field(min_length=1, max_length=600)
    language: Literal["fr"] = "fr"
    session_id: UUID | None = None
    target_id: str | None = Field(default=None, max_length=100)


class SpeechText(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    request_id: UUID
    reviewed_turn_id: UUID | None = None


class UtteranceReview(StrictModel):
    source_turn_id: UUID
    original_text: str = Field(max_length=4000)
    confirmed_text: str = Field(max_length=4000)
    confirmed_at: datetime
    edited: bool


class AudioView(StrictModel):
    status: Literal["ready", "unavailable", "deleted", "expired"]
    asset_id: UUID | None = None
    spoken_text: str | None = None
    voice: str | None = None
    duration_ms: int | None = None


class TurnView(StrictModel):
    id: UUID
    request_id: UUID
    transcript: str
    transcription_status: str
    transcription: Transcription | None = None
    review: UtteranceReview | None = None
    tutor: ChatResponse | None = None
    tutor_audio: AudioView
    input_audio_id: UUID | None = None
    status: str
    created_at: datetime


class SpeechSessionView(StrictModel):
    id: UUID
    conversation_id: UUID
    cefr_level: Level
    scenario_id: str | None
    status: str
    title: str
    draft_preview: bool
    created_at: datetime
    last_activity_at: datetime
    turns: list[TurnView] = []
    has_more_turns: bool = False


class Target(StrictModel):
    id: str
    text: str
    english: str
    level: Level
    lesson_id: UUID
    content_version: str
    draft_preview: bool
    guidance: str


class AttemptView(StrictModel):
    id: UUID
    request_id: UUID
    target: Target
    recognized_text: str
    recognition_match: bool | None
    recognition_feedback: str
    assessment_status: Literal["not_available", "insufficient_audio"]
    acoustic_score: None = None
    limitations: str
    transcription: Transcription
    input_audio_id: UUID | None
    created_at: datetime
