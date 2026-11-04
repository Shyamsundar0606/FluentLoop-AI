from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.learning_models import LessonProgress
from app.models import User


def ensure_lesson_progress(
    db: Session,
    *,
    user: User,
    lesson_id: UUID,
    cefr_level: str,
    now: datetime | None = None,
) -> LessonProgress:
    now = now or datetime.now(timezone.utc)
    progress = db.scalar(
        select(LessonProgress)
        .where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson_id,
        )
        .with_for_update()
    )
    if progress is None:
        progress = LessonProgress(
            user_id=user.id,
            lesson_id=lesson_id,
            cefr_level=cefr_level,
            status="in_progress",
            first_started_at=now,
            last_studied_at=now,
        )
        db.add(progress)
    else:
        progress.cefr_level = cefr_level
        if progress.status != "completed":
            progress.status = "in_progress"
        if progress.first_started_at is None:
            progress.first_started_at = now
        progress.last_studied_at = now
        progress.updated_at = now
    return progress


def record_completion(
    progress: LessonProgress,
    *,
    score_percentage: float,
    completed_at: datetime,
) -> None:
    progress.status = "completed"
    progress.completed_at = completed_at
    progress.last_studied_at = completed_at
    progress.latest_score = score_percentage
    progress.best_score = max(float(progress.best_score), score_percentage)
    progress.completion_count += 1
    progress.updated_at = completed_at
