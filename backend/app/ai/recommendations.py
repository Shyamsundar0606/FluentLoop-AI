"""Deterministic recommendations from actual missed exercises, without answer text."""

from collections import defaultdict
from sqlalchemy import select
from app.ai.models import Recommendation
from app.curriculum_models import Lesson, Unit, Course
from app.learning_models import ExerciseAttempt, LearningSession
from app.ai.retrieval import source_for
from app.api.v1.curriculum import _published_lesson_filter
from app.services.draft_preview import can_preview_drafts
from app.models import utcnow


def refresh(db, user):
    level = user.preferences.current_level.upper()
    # Serialize refreshes per owner on PostgreSQL to avoid duplicate recommendations.
    from app.models import User

    db.scalar(select(User).where(User.id == user.id).with_for_update())
    rows = db.execute(
        select(ExerciseAttempt.id, LearningSession.lesson_id)
        .join(
            LearningSession, LearningSession.id == ExerciseAttempt.learning_session_id
        )
        .join(Lesson, Lesson.id == LearningSession.lesson_id)
        .join(Unit, Unit.id == Lesson.unit_id)
        .join(Course, Course.id == Unit.course_id)
        .where(
            ExerciseAttempt.user_id == user.id,
            LearningSession.user_id == user.id,
            ExerciseAttempt.is_correct.is_(False),
            LearningSession.cefr_level == level,
            _published_lesson_filter(can_preview_drafts(user)),
            (
                LearningSession.preview_mode.is_(False)
                if not can_preview_drafts(user)
                else True
            ),
        )
        .order_by(ExerciseAttempt.submitted_at.desc())
        .limit(200)
    ).all()
    grouped = defaultdict(list)
    for attempt_id, lesson_id in rows:
        grouped[lesson_id].append(str(attempt_id))
    existing = db.scalars(
        select(Recommendation).where(
            Recommendation.user_id == user.id, Recommendation.cefr_level == level
        )
    ).all()
    for item in existing:
        item.status = "superseded"
    eligible = []
    for lesson_id, ids in sorted(
        grouped.items(), key=lambda item: (-len(item[1]), str(item[0]))
    ):
        if len(ids) < 2:
            continue
        lesson = db.get(Lesson, lesson_id)
        eligible.append(
            (
                lesson.title[:120],
                "lesson_review",
                f"You missed {len(ids)} exercises in this lesson among your latest 200 incorrect attempts. Review the lesson topics.",
                lesson_id,
                {"exercise_attempt_ids": ids},
            )
        )
        if len(eligible) == 5:
            break
    if not eligible:
        lesson = db.scalar(
            select(Lesson)
            .join(Unit, Unit.id == Lesson.unit_id)
            .join(Course, Course.id == Unit.course_id)
            .where(
                Course.level_id == level,
                _published_lesson_filter(can_preview_drafts(user)),
            )
            .order_by(Unit.sequence_order, Lesson.sequence_order)
            .limit(1)
        )
        eligible = [
            (
                "Getting started",
                "introduction",
                "There is not enough repeated-error evidence to identify weak topics. Try an available lesson or ask the tutor a question.",
                lesson.id if lesson else None,
                {},
            )
        ]
    for topic, kind, reason, lesson_id, evidence in eligible:
        item = next((r for r in existing if r.topic == topic), None)
        if item is None:
            item = Recommendation(user_id=user.id, cefr_level=level, topic=topic)
            db.add(item)
            existing.append(item)
        item.recommendation_type = kind
        item.reason = reason
        item.linked_lesson_id = lesson_id
        item.source_activity_reference = evidence
        item.status = "active"
        item.updated_at = utcnow()
    db.commit()
    return list_recommendations(db, user)


def list_recommendations(db, user):
    from fastapi import HTTPException

    rows = db.scalars(
        select(Recommendation)
        .where(
            Recommendation.user_id == user.id,
            Recommendation.cefr_level == user.preferences.current_level.upper(),
            Recommendation.status == "active",
        )
        .order_by(Recommendation.created_at.desc())
        .limit(10)
    ).all()
    result = []
    for item in rows:
        source = None
        if item.linked_lesson_id:
            try:
                source = source_for(db, user, item.linked_lesson_id).model_dump(
                    mode="json"
                )
            except HTTPException:
                continue
        result.append(
            {
                "id": str(item.id),
                "topic": item.topic,
                "reason": item.reason,
                "cefr_level": item.cefr_level,
                "recommendation_type": item.recommendation_type,
                "source_activity_reference": item.source_activity_reference,
                "lesson": source,
                "suggested_action": "Open lesson" if source else "Ask the tutor",
            }
        )
    return result
