"""Objective practice assessments backed by the existing frozen session engine."""
from fastapi import HTTPException
from sqlalchemy import select

from app.curriculum_models import Lesson, LearningObjective, LessonSection, LessonObjective
from app.learning_models import LearningSession
from app.services import interactive_learning, learning_service
from app.services.draft_preview import can_preview_drafts

SKILLS = ("grammar", "vocabulary", "reading", "listening")
POLICY_VERSION = "objective-v1"


def task_context(db, lesson_id, skill):
    sections = db.scalars(select(LessonSection).where(LessonSection.lesson_id == lesson_id)
                          .order_by(LessonSection.sequence_order)).all()
    return "\n\n".join(section.body_content for section in sections
                       if section.content_metadata.get("assessment_skill") == skill)


def candidates(db, user, level, skill, lesson_id=None):
    rows = interactive_learning.candidates(db, user, level, skill, lesson_id=lesson_id)
    if skill in ("vocabulary", "reading"):
        objectives = set(db.scalars(select(LearningObjective.id).where(
            LearningObjective.skill_category == skill, LearningObjective.level == level)).all())
        rows = [exercise for exercise in rows if exercise.learning_objective_id in objectives]
        if skill == "reading":
            contexts = {row.lesson_id: task_context(db, row.lesson_id, skill) for row in rows}
            rows = [row for row in rows if contexts[row.lesson_id]]
    return rows


def catalog(db, user, level=None):
    level = level or user.preferences.current_level.upper()
    items = []
    for skill in SKILLS:
        groups = {}
        for exercise in candidates(db, user, level, skill):
            groups.setdefault(exercise.lesson_id, []).append(exercise)
        for lesson_id, exercises in groups.items():
            lesson = db.get(Lesson, lesson_id)
            count = min(len(exercises), 12)
            objectives = db.scalars(select(LearningObjective).where(LearningObjective.id.in_(
                [exercise.learning_objective_id for exercise in exercises[:12] if exercise.learning_objective_id]
            )).order_by(LearningObjective.code)).all()
            items.append(dict(
                id=f"{skill}:{lesson_id}", skill=skill, lesson_id=str(lesson_id),
                title=lesson.title, level=level, question_count=count,
                duration_minutes=count * 2, content_version=lesson.content_version,
                scoring_policy=POLICY_VERSION,
                objectives=[dict(title=objective.title, description=objective.description) for objective in objectives],
            ))
    from app.services import study_content
    for lesson, _ in study_content.lessons(db, user, level):
        objective = db.scalar(select(LearningObjective).join(
            LessonObjective, LearningObjective.id == LessonObjective.objective_id).where(
                LessonObjective.lesson_id == lesson.id, LearningObjective.level == level,
                LearningObjective.skill_category == "writing"))
        if task_context(db, lesson.id, "writing") and objective:
            items.append(dict(id=f"writing:{lesson.id}", skill="writing", lesson_id=str(lesson.id),
                title=lesson.title, level=level, question_count=1, duration_minutes=6,
                content_version=lesson.content_version, scoring_policy="advisory-only",
                objectives=[dict(title=objective.title, description=objective.description)]))
    return dict(level=level, draft_preview=can_preview_drafts(user), items=items)


def start(db, user, skill, lesson_id):
    # Derive the level from the permitted lesson, never from an unchecked request.
    lesson, _, _, _ = learning_service._accessible_lesson(db, lesson_id, user)
    level = lesson.difficulty_level
    rows = candidates(db, user, level, skill, lesson_id=lesson_id)
    if not rows:
        raise HTTPException(404, "This assessment is unavailable at your selected level.")
    result, created = learning_service.start_session(
        db, user=user, lesson_id=lesson_id,
        activity_key=f"assessment:{skill}:{POLICY_VERSION}",
        exercise_ids=[exercise.id for exercise in rows[:12]], commit=False,
    )
    if created:
        session = db.get(LearningSession, result.id)
        session.lesson_snapshot = {**session.lesson_snapshot,
            "assessment_context": task_context(db, lesson_id, skill)}
        db.flush()
        result = learning_service.get_session(db, user=user, session_id=session.id)
    db.commit()
    return result


def history(db, user, limit, offset):
    # Bound the read and reapply the engine's complete live permission checks,
    # including topics referenced by frozen lesson and exercise snapshots.
    sessions = db.scalars(select(LearningSession).where(
        LearningSession.user_id == user.id,
        LearningSession.activity_key.in_(
            [f"assessment:{skill}:{POLICY_VERSION}" for skill in SKILLS]),
    ).order_by(LearningSession.started_at.desc(), LearningSession.id.desc())
        .offset(offset).limit(limit + 1)).all()
    items = []
    for session in sessions[:limit]:
        if session.preview_mode and not can_preview_drafts(user):
            continue
        try:
            learning_service._session_for_user(db, session.id, user)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            continue
        items.append(dict(
            id=str(session.id), skill=session.activity_key.split(":")[1],
            title=session.lesson_snapshot["title"], level=session.cefr_level,
            status=session.status, started_at=session.started_at,
            completed_at=session.completed_at, answered=session.current_exercise_position,
            question_count=session.total_exercises, score_points=session.score_points,
            max_score_points=session.max_score_points,
            percentage=learning_service._percentage(session.score_points, session.max_score_points)
                if session.max_score_points else None,
            draft_preview=session.preview_mode,
        ))
    return dict(items=items, limit=limit, offset=offset,
                next_offset=offset + limit if len(sessions) > limit else None)


def insights(db, user):
    page = history(db, user, 100, 0)
    level = user.preferences.current_level.upper()
    items = [item for item in page["items"] if item["level"] == level]
    skills = []
    for skill in SKILLS:
        completed = [item for item in items if item["skill"] == skill and item["status"] == "completed"]
        points = sum(item["score_points"] for item in completed)
        maximum = sum(item["max_score_points"] for item in completed)
        skills.append(dict(
            skill=skill, completed_sessions=len(completed), correct_answers=points,
            answered_questions=maximum, percentage=round(100 * points / maximum, 2) if maximum else None,
            evidence="Recorded practice" if maximum else "Insufficient evidence",
        ))
    unresolved = {}
    for mistake in interactive_learning.mistakes(db, user, level)["items"]:
        key = (mistake["lesson_id"], mistake["learning_objective_id"])
        item = unresolved.setdefault(key, dict(title=mistake["objective_title"] or mistake["lesson_title"],
            unresolved_questions=0, url=f"/practice?level={level.lower()}&category=mistakes&lesson={mistake['lesson_id']}"))
        item["unresolved_questions"] += 1
    recommendations = sorted(unresolved.values(), key=lambda item: (-item["unresolved_questions"], item["title"]))[:5]
    return dict(level=level, sample_limit=100, has_older_history=page["next_offset"] is not None,
                recommendations=recommendations, mistake_attempt_window=200,
                skills=skills, notice="Practice evidence only. This is not an official CEFR evaluation.")
