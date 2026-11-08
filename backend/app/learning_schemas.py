from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.content_schemas import CEFR


class LearningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartSessionRequest(LearningRequest):
    lesson_id: UUID


class SessionPositionRequest(LearningRequest):
    position: int = Field(ge=0, le=3, strict=True)


class SubmitAnswerRequest(LearningRequest):
    session_exercise_id: UUID
    selected_option_id: UUID | None = None
    text_answer: str | None = Field(default=None, min_length=1, max_length=1000)
    tile_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=30)
    matches: dict[UUID, UUID] | None = Field(default=None, min_length=1, max_length=12)
    idempotency_key: UUID

    @model_validator(mode="after")
    def one_answer_shape(self):
        if sum(value is not None for value in (self.selected_option_id,self.text_answer,self.tile_ids,self.matches)) != 1:
            raise ValueError("Supply exactly one answer format")
        return self


class PracticeRequest(LearningRequest):
    category: Literal['grammar','sentence_building','listening','mistakes']
    level: CEFR | None = None
    grammar_topic_id: UUID | None = None
    learning_objective_id: UUID | None = None
    lesson_id: UUID | None = None
    attempt_id: UUID | None = None


class SessionExerciseOption(BaseModel):
    id: UUID
    text: str
    sequence_order: int


class ExerciseFeedback(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str
    awarded_points: int
    max_points: int
    answered_at: datetime


class SessionExerciseResponse(BaseModel):
    id: UUID
    exercise_id: UUID | None
    exercise_order: int
    type: str
    prompt: str
    instructions: str
    options: list[SessionExerciseOption]
    answered: bool
    feedback: ExerciseFeedback | None = None
    tiles: list[dict[str, str]] = Field(default_factory=list)
    left_items: list[dict[str, str]] = Field(default_factory=list)
    right_items: list[dict[str, str]] = Field(default_factory=list)
    submitted_answer: dict[str, Any] | None = None
    learning_objective_id: UUID | None = None
    grammar_topic_id: UUID | None = None


class LearningSessionResponse(BaseModel):
    id: UUID
    lesson_id: UUID
    lesson_content_version: str
    cefr_level: CEFR
    status: Literal["in_progress", "completed", "abandoned"]
    preview_mode: bool
    started_at: datetime
    last_activity_at: datetime
    completed_at: datetime | None
    current_section_position: int
    current_exercise_position: int
    total_exercises: int
    answered_exercises: int
    score_points: int
    max_score_points: int
    percentage: float
    lesson: dict[str, Any]
    exercises: list[SessionExerciseResponse]
    activity_key: str = 'lesson'


class SessionListItem(BaseModel):
    id: UUID
    lesson_id: UUID
    lesson_title: str
    cefr_level: CEFR
    lesson_content_version: str
    status: Literal["in_progress", "completed", "abandoned"]
    started_at: datetime
    last_activity_at: datetime
    completed_at: datetime | None
    total_exercises: int
    answered_exercises: int
    percentage: float
    activity_key: str = 'lesson'


class SessionListResponse(BaseModel):
    items: list[SessionListItem]
    limit: int
    offset: int
    total: int


class AnswerResponse(BaseModel):
    session_id: UUID
    session_exercise_id: UUID
    is_correct: bool
    correct_answer: str
    explanation: str
    awarded_points: int
    max_points: int
    answered_exercises: int
    total_exercises: int
    score_points: int
    max_score_points: int
    percentage: float
    idempotent_replay: bool = False


class CompletionResponse(BaseModel):
    session_id: UUID
    lesson_id: UUID
    lesson_title: str
    cefr_level: CEFR
    status: Literal["completed"]
    correct_answers: int
    incorrect_answers: int
    total_questions: int
    score_points: int
    max_score_points: int
    percentage: float
    completion_count: int
    completed_at: datetime
    activity_key: str = 'lesson'


class LessonProgressResponse(BaseModel):
    lesson_id: UUID
    lesson_title: str
    cefr_level: CEFR
    status: Literal["not_started", "in_progress", "completed"]
    first_started_at: datetime | None
    last_studied_at: datetime | None
    completed_at: datetime | None
    best_score: float
    latest_score: float
    completion_count: int


class ProgressResponse(BaseModel):
    items: list[LessonProgressResponse]
    limit: int
    offset: int
    total: int


class LearningDashboardResponse(BaseModel):
    current_level: CEFR
    lessons_started: int = Field(ge=0)
    lessons_completed: int = Field(ge=0)
    lessons_in_progress: int = Field(ge=0)
    active_sessions: list[SessionListItem]
    total_answered_exercises: int = Field(ge=0)
    average_completed_session_score: float
    recent_activity: list[dict[str, Any]]
    learning_path: list[dict[str, Any]]
