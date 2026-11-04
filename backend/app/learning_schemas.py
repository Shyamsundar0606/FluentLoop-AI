from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.content_schemas import CEFR


class LearningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartSessionRequest(LearningRequest):
    lesson_id: UUID


class SubmitAnswerRequest(LearningRequest):
    session_exercise_id: UUID
    selected_option_id: UUID
    idempotency_key: UUID


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
