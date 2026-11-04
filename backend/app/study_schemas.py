from datetime import date, datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

Level = Literal['A1','A2','B1','B2','C1','C2']
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class GeneratePlan(Strict):
    request_id: UUID
    regenerate: bool = False

class StartReview(Strict):
    request_id: UUID
    limit: int = Field(3, ge=1, le=20)

class AnswerReview(Strict):
    request_id: UUID
    item_id: UUID
    answer: str = Field(min_length=1, max_length=300)
    recall_rating: Literal['easy','normal','difficult'] | None = None

    @field_validator('answer')
    @classmethod
    def nonempty(cls, value):
        if not value.strip() or any(ord(c) < 32 and c not in '\t\n\r' for c in value):
            raise ValueError('Enter a valid answer.')
        return value

class ActivityView(BaseModel):
    id: UUID
    activity_type: str
    title: str
    reason: str
    estimated_minutes: int
    status: str
    sequence_order: int
    draft_preview: bool
    url: str | None
    completion_available: bool

class PlanView(BaseModel):
    id: UUID
    cefr_level: Level
    local_study_date: date
    timezone_name: str
    target_minutes: int
    planned_minutes: int
    status: str
    plan_version: str
    generation: int
    activities: list[ActivityView]
    unavailable_activity_count: int
    due_review_count: int
    generated_at: datetime
    completed_at: datetime | None

class RecommendationView(BaseModel):
    activity_type: str
    title: str
    reason: str
    priority: int
    lesson_id: UUID | None = None
    draft_preview: bool = False
    evidence_attempt_ids: list[UUID] = []

class QuestionView(BaseModel):
    item_id: UUID
    card_id: UUID
    sequence_order: int
    prompt: str
    answer_type: Literal['typed_french'] = 'typed_french'
    draft_preview: bool

class ReviewFeedback(BaseModel):
    id: UUID
    item_id: UUID
    card_id: UUID
    submitted_answer: str
    is_correct: bool
    correct_answer: str
    explanation: str
    recall_rating: str | None
    next_due_at: datetime

class ReviewSessionView(BaseModel):
    id: UUID
    cefr_level: Level
    status: str
    total_cards: int
    answered_cards: int
    unavailable_cards: int
    current_question: QuestionView | None
    feedback: list[ReviewFeedback]

class DueView(BaseModel):
    cefr_level: Level
    due_count: int
    available_vocabulary_count: int
    new_vocabulary_count: int
    next_due_at: datetime | None

class ReviewProgress(BaseModel):
    reviews_completed: int
    cards_due: int
    vocabulary_items_studied: int

class HistoryView(BaseModel):
    id: UUID
    session_id: UUID
    card_id: UUID
    cefr_level: Level
    is_correct: bool
    reviewed_at: datetime
    next_due_at: datetime
    algorithm_version: str

class PlanPage(BaseModel):
    items: list[PlanView]
    limit: int
    offset: int

class HistoryPage(BaseModel):
    items: list[HistoryView]
    limit: int
    offset: int
