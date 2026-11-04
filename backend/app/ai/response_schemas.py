from typing import Literal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

Level = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
Mode = Literal["tutor", "vocabulary", "grammar", "correction", "roleplay"]


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        from_attributes=True,
        protected_namespaces=(),
    )


class CreateConversation(StrictModel):
    title: str = Field(default="French practice", min_length=1, max_length=120)
    mode: Mode = "tutor"
    linked_lesson_id: UUID | None = None


class RenameConversation(StrictModel):
    title: str = Field(min_length=1, max_length=120)


class SendMessage(StrictModel):
    message: str = Field(min_length=1, max_length=4000)
    request_id: UUID


class Correction(StrictModel):
    original_text: str = Field(min_length=1, max_length=4000)
    corrected_text: str = Field(min_length=1, max_length=4000)
    has_errors: bool
    explanations: list[str] = Field(max_length=8)
    alternative_expressions: list[str] = Field(default_factory=list, max_length=4)
    level: Level
    model_notes: str = Field(default="", max_length=1000)


class CorrectionRequest(SendMessage):
    conversation_id: UUID


class Source(StrictModel):
    lesson_id: UUID
    source_type: Literal["lesson"] = "lesson"
    source_record_id: UUID
    title: str
    content_version: str
    draft_preview: bool
    url: str


class MessageView(StrictModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    response_status: str
    grounding_status: str
    request_id: UUID | None
    sources: list[Source] = []
    correction: Correction | None = None


class ConversationView(StrictModel):
    id: UUID
    title: str
    mode: Mode
    cefr_level: Level
    scenario_id: str | None
    status: Literal["active", "archived"]
    preview_mode: bool
    updated_at: datetime
    messages: list[MessageView] = []
    has_more_messages: bool = False


class ChatResponse(StrictModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    cefr_level: Level
    grounding_status: str
    sources: list[Source]
    suggested_actions: list[dict] = []
    model: dict
    correction: Correction | None = None


class HealthView(StrictModel):
    available: bool
    provider: str
    message: str


class RecommendationView(StrictModel):
    id: UUID
    topic: str
    reason: str
    cefr_level: Level
    recommendation_type: Literal["lesson_review", "introduction"]
    source_activity_reference: dict
    lesson: Source | None
    suggested_action: str


class FeedbackView(StrictModel):
    id: UUID
    cefr_level: Level
    topic: str
    feedback_type: Literal["correction"]
    corrected_text: str
    explanation: str
