from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.config import Settings
from app.content_import import _import_data, load_content
from app.core.database import Base
from app.curriculum_models import (
    CefrLevel,
    Course,
    Exercise,
    ExerciseOption,
    Lesson,
    Unit,
)
from app.learning_models import (
    ExerciseAttempt,
    LearningActivityEvent,
    LearningSession,
    LearningSessionExercise,
    LessonProgress,
)
from app.models import User

CONTENT_PATH = Path(__file__).resolve().parents[1] / "content" / "a1" / "course.json"
PASSWORD = "StrongLearningPass2026"


def _register_and_login(client: TestClient, email_service, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "display_name": "Learning Test",
        },
    )
    assert response.status_code == 201
    match = re.search(
        r"/verify-email#token=([A-Za-z0-9_-]+)",
        email_service.messages[-1]["body"],
    )
    assert match
    verified = client.post("/api/v1/auth/verify-email", json={"token": match.group(1)})
    assert verified.status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    ).status_code == 200


def _csrf(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("fluentloop_csrf")
    assert token
    return {"X-CSRF-Token": token}


def _import_content(sessions) -> None:
    content = load_content(CONTENT_PATH)
    with sessions.begin() as db:
        if db.scalar(select(func.count(CefrLevel.id))) == 0:
            db.add_all(
                [
                    CefrLevel(
                        code=level,
                        display_name=level,
                        description=f"{level} French",
                        rank=rank,
                    )
                    for rank, level in enumerate(("A1", "A2", "B1", "B2", "C1", "C2"), start=1)
                ]
            )
            db.flush()
        _import_data(db, content)


def _set_role(sessions, email: str, role: str) -> None:
    with sessions.begin() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = role


def _draft_lesson_id(sessions) -> UUID:
    with sessions() as db:
        course = db.scalar(select(Course).where(Course.slug == "a1-french-from-the-beginning"))
        assert course is not None
        lesson = db.scalar(
            select(Lesson)
            .join(Unit, Lesson.unit_id == Unit.id)
            .where(Unit.course_id == course.id, Lesson.slug == "a1-001")
        )
        assert lesson is not None and lesson.status == "draft"
        return lesson.id


def test_learning_grading_idempotency_resume_completion_and_retake(
    api_client,
    monkeypatch,
):
    client, sessions, emails = api_client
    _register_and_login(client, emails, "learning-admin@example.com")
    _set_role(sessions, "learning-admin@example.com", "admin")
    monkeypatch.setattr(
        "app.services.draft_preview.get_settings",
        lambda: Settings(_env_file=None, APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=True),
    )
    _import_content(sessions)
    lesson_id = _draft_lesson_id(sessions)

    start = client.post(
        "/api/v1/learning/sessions",
        headers=_csrf(client),
        json={"lesson_id": str(lesson_id)},
    )
    assert start.status_code == 201
    first = start.json()
    session_id = first["id"]
    assert first["preview_mode"] is True
    assert first["total_exercises"] == 5
    assert "correct_option_id" not in start.text
    assert "accepted_answer" not in start.text
    assert "correct_answer" not in start.text
    assert "is_correct" not in start.text

    duplicate_start = client.post(
        "/api/v1/learning/sessions",
        headers=_csrf(client),
        json={"lesson_id": str(lesson_id)},
    )
    assert duplicate_start.status_code == 200
    assert duplicate_start.json()["id"] == session_id

    with sessions() as db:
        source_exercise = db.scalar(
            select(Exercise)
            .join(Lesson, Exercise.lesson_id == Lesson.id)
            .where(Lesson.id == lesson_id, Exercise.sequence_order == 1)
        )
        assert source_exercise is not None
        source_options = db.scalars(
            select(ExerciseOption)
            .where(ExerciseOption.exercise_id == source_exercise.id)
            .order_by(ExerciseOption.sequence_order)
        ).all()
        correct_option = next(option for option in source_options if option.is_correct)
        wrong_option = next(option for option in source_options if not option.is_correct)
        snapshot = db.scalar(
            select(LearningSessionExercise).where(
                LearningSessionExercise.learning_session_id == UUID(session_id),
                LearningSessionExercise.exercise_order == 1,
            )
        )
        assert snapshot is not None
    first_question_id = first["exercises"][0]["id"]
    idem_key = str(uuid4())
    correct_answer = client.post(
        f"/api/v1/learning/sessions/{session_id}/answers",
        headers=_csrf(client),
        json={
            "session_exercise_id": first_question_id,
            "selected_option_id": str(correct_option.id),
            "idempotency_key": idem_key,
        },
    )
    assert correct_answer.status_code == 200
    assert correct_answer.json()["is_correct"] is True
    assert correct_answer.json()["score_points"] == 1
    assert correct_answer.json()["idempotent_replay"] is False

    replay = client.post(
        f"/api/v1/learning/sessions/{session_id}/answers",
        headers=_csrf(client),
        json={
            "session_exercise_id": first_question_id,
            "selected_option_id": str(correct_option.id),
            "idempotency_key": idem_key,
        },
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["score_points"] == 1

    conflict = client.post(
        f"/api/v1/learning/sessions/{session_id}/answers",
        headers=_csrf(client),
        json={
            "session_exercise_id": first_question_id,
            "selected_option_id": str(wrong_option.id),
            "idempotency_key": idem_key,
        },
    )
    assert conflict.status_code == 409

    restored = client.post(
        f"/api/v1/learning/sessions/{session_id}/resume",
        headers=_csrf(client),
    )
    assert restored.status_code == 200
    restored_body = restored.json()
    assert restored_body["answered_exercises"] == 1
    assert restored_body["exercises"][0]["feedback"]["is_correct"] is True
    assert restored_body["exercises"][1]["feedback"] is None
    assert "correct_option_id" not in restored.text

    second_question = restored_body["exercises"][1]
    with sessions() as db:
        second_snapshot = db.get(LearningSessionExercise, UUID(second_question["id"]))
        assert second_snapshot is not None
        second_correct_id = second_snapshot.exercise_snapshot["correct_option_id"]
        second_wrong_id = next(
            item["id"]
            for item in second_snapshot.exercise_snapshot["options"]
            if item["id"] != second_correct_id
        )
    incorrect_answer = client.post(
        f"/api/v1/learning/sessions/{session_id}/answers",
        headers=_csrf(client),
        json={
            "session_exercise_id": second_question["id"],
            "selected_option_id": second_wrong_id,
            "idempotency_key": str(uuid4()),
        },
    )
    assert incorrect_answer.status_code == 200
    assert incorrect_answer.json()["is_correct"] is False
    assert incorrect_answer.json()["score_points"] == 1

    incomplete = client.post(
        f"/api/v1/learning/sessions/{session_id}/complete",
        headers=_csrf(client),
    )
    assert incomplete.status_code == 409

    for order in range(3, 6):
        state = client.get(f"/api/v1/learning/sessions/{session_id}")
        assert state.status_code == 200
        exercise = state.json()["exercises"][order - 1]
        with sessions() as db:
            snapshot = db.get(LearningSessionExercise, UUID(exercise["id"]))
            assert snapshot is not None
            option_id = snapshot.exercise_snapshot["correct_option_id"]
        response = client.post(
            f"/api/v1/learning/sessions/{session_id}/answers",
            headers=_csrf(client),
            json={
                "session_exercise_id": exercise["id"],
                "selected_option_id": option_id,
                "idempotency_key": str(uuid4()),
            },
        )
        assert response.status_code == 200

    completed = client.post(
        f"/api/v1/learning/sessions/{session_id}/complete",
        headers=_csrf(client),
    )
    assert completed.status_code == 200
    result = completed.json()
    assert result["status"] == "completed"
    assert result["correct_answers"] == 4
    assert result["incorrect_answers"] == 1
    assert result["percentage"] == 80
    assert result["completion_count"] == 1

    repeated_complete = client.post(
        f"/api/v1/learning/sessions/{session_id}/complete",
        headers=_csrf(client),
    )
    assert repeated_complete.status_code == 200
    assert repeated_complete.json()["completion_count"] == 1
    after_completion = client.post(
        f"/api/v1/learning/sessions/{session_id}/answers",
        headers=_csrf(client),
        json={
            "session_exercise_id": first_question_id,
            "selected_option_id": str(correct_option.id),
            "idempotency_key": str(uuid4()),
        },
    )
    assert after_completion.status_code == 409

    persisted_progress = client.get("/api/v1/learning/progress")
    assert persisted_progress.status_code == 200
    assert persisted_progress.json()["total"] == 1
    progress = persisted_progress.json()["items"][0]
    assert progress["status"] == "completed"
    assert progress["completion_count"] == 1
    assert progress["best_score"] == 80
    assert progress["latest_score"] == 80

    dashboard = client.get("/api/v1/learning/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["lessons_completed"] == 1
    assert dashboard.json()["total_answered_exercises"] == 5
    assert dashboard.json()["average_completed_session_score"] == 80

    assert client.patch(
        "/api/v1/users/me/preferences",
        headers=_csrf(client),
        json={"current_level": "b1"},
    ).status_code == 200
    old_level_progress = client.get("/api/v1/learning/progress")
    assert old_level_progress.json()["items"][0]["cefr_level"] == "A1"

    retake = client.post(
        "/api/v1/learning/sessions",
        headers=_csrf(client),
        json={"lesson_id": str(lesson_id)},
    )
    assert retake.status_code == 201
    assert retake.json()["id"] != session_id
    frozen_session_id = retake.json()["id"]
    frozen_question = retake.json()["exercises"][0]
    with sessions.begin() as db:
        lesson = db.get(Lesson, lesson_id)
        assert lesson is not None
        exercise = db.scalar(
            select(Exercise).where(
                Exercise.lesson_id == lesson.id,
                Exercise.sequence_order == 1,
            )
        )
        assert exercise is not None
        options = db.scalars(
            select(ExerciseOption).where(ExerciseOption.exercise_id == exercise.id)
        ).all()
        original_correct = next(option for option in options if option.is_correct)
        original_incorrect = next(option for option in options if not option.is_correct)
        lesson.content_version = "1.0.3"
        exercise.prompt = "Updated source prompt after session start."
        original_correct.is_correct = False
        original_incorrect.is_correct = True
    frozen_state = client.post(
        f"/api/v1/learning/sessions/{frozen_session_id}/resume",
        headers=_csrf(client),
    )
    assert frozen_state.status_code == 200
    frozen_question_after_edit = frozen_state.json()["exercises"][0]
    assert frozen_state.json()["lesson_content_version"] == "1.0.2"
    assert frozen_question_after_edit["prompt"] == frozen_question["prompt"]
    assert frozen_state.json()["lesson"]["content_version"] == "1.0.2"
    frozen_answer = client.post(
        f"/api/v1/learning/sessions/{frozen_session_id}/answers",
        headers=_csrf(client),
        json={
            "session_exercise_id": frozen_question["id"],
            "selected_option_id": str(original_correct.id),
            "idempotency_key": str(uuid4()),
        },
    )
    assert frozen_answer.status_code == 200
    assert frozen_answer.json()["is_correct"] is True
    assert client.post(
        f"/api/v1/learning/sessions/{frozen_session_id}/abandon",
        headers=_csrf(client),
    ).status_code == 200
    new_version_session = client.post(
        "/api/v1/learning/sessions",
        headers=_csrf(client),
        json={"lesson_id": str(lesson_id)},
    )
    assert new_version_session.status_code == 201
    assert new_version_session.json()["lesson_content_version"] == "1.0.3"
    assert new_version_session.json()["exercises"][0]["prompt"] == "Updated source prompt after session start."
    assert client.post(
        f"/api/v1/learning/sessions/{new_version_session.json()['id']}/abandon",
        headers=_csrf(client),
    ).status_code == 200
    with sessions() as db:
        assert db.scalar(select(func.count(ExerciseAttempt.id))) == 6
        assert db.scalar(select(func.count(LessonProgress.id))) == 1


def test_draft_preview_production_gate_and_user_session_isolation(api_client, monkeypatch):
    client_a, sessions, emails = api_client
    email_a = "learning-user-a@example.com"
    _register_and_login(client_a, emails, email_a)
    _import_content(sessions)
    lesson_id = _draft_lesson_id(sessions)

    learner_courses = client_a.get("/api/v1/courses?level=A1")
    assert learner_courses.status_code == 200
    assert learner_courses.json()["items"] == []
    assert client_a.get(f"/api/v1/lessons/{lesson_id}").status_code == 404
    assert client_a.post(
        "/api/v1/learning/sessions",
        json={"lesson_id": str(lesson_id)},
    ).status_code == 403
    assert client_a.get(
        f"/api/v1/lessons/{lesson_id}?preview=true",
        headers={"X-Draft-Preview": "true"},
    ).status_code == 404
    assert client_a.get(f"/api/v1/lessons/{lesson_id}/exercises").status_code == 404
    assert client_a.get(f"/api/v1/learning/progress/lessons/{lesson_id}").status_code == 404
    assert client_a.post(
        "/api/v1/learning/sessions",
        headers=_csrf(client_a),
        json={"lesson_id": str(lesson_id), "preview": True},
    ).status_code == 422

    dev_settings = Settings(
        _env_file=None,
        APP_ENV="development",
        ENABLE_DRAFT_LEARNING_PREVIEW=True,
    )
    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: dev_settings)
    assert client_a.get("/api/v1/courses?level=A1").json()["items"] == []
    _set_role(sessions, email_a, "admin")
    preview_courses = client_a.get("/api/v1/courses?level=A1")
    assert preview_courses.status_code == 200
    assert preview_courses.json()["items"][0]["draft_preview"] is True
    assert client_a.get(f"/api/v1/lessons/{lesson_id}").json()["draft_preview"] is True

    prod_settings = Settings(
        _env_file=None,
        APP_ENV="production",
        COOKIE_SECURE=True,
        ENABLE_DRAFT_LEARNING_PREVIEW=True,
    )
    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: prod_settings)
    assert prod_settings.draft_learning_preview_enabled is False
    assert client_a.get("/api/v1/courses?level=A1").json()["items"] == []
    assert client_a.get(f"/api/v1/lessons/{lesson_id}").status_code == 404
    assert client_a.post(
        "/api/v1/learning/sessions",
        headers=_csrf(client_a),
        json={"lesson_id": str(lesson_id)},
    ).status_code == 404

    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: dev_settings)
    started = client_a.post(
        "/api/v1/learning/sessions",
        headers=_csrf(client_a),
        json={"lesson_id": str(lesson_id)},
    )
    assert started.status_code == 201
    session_id = started.json()["id"]
    exercise = started.json()["exercises"][0]
    with sessions() as db:
        saved_exercise = db.get(LearningSessionExercise, UUID(exercise["id"]))
        assert saved_exercise is not None
        selected_option_id = saved_exercise.exercise_snapshot["options"][0]["id"]
    assert client_a.post(
        f"/api/v1/learning/sessions/{session_id}/answers",
        headers=_csrf(client_a),
        json={
            "session_exercise_id": exercise["id"],
            "selected_option_id": selected_option_id,
            "idempotency_key": str(uuid4()),
        },
    ).status_code == 200

    client_b = TestClient(
        client_a.app,
        headers={"Origin": "http://localhost:3000"},
    )
    _register_and_login(client_b, emails, "learning-user-b@example.com")
    _set_role(sessions, "learning-user-b@example.com", "admin")
    assert client_b.get(f"/api/v1/learning/sessions/{session_id}").status_code == 404
    assert client_b.post(
        f"/api/v1/learning/sessions/{session_id}/resume",
        headers=_csrf(client_b),
    ).status_code == 404
    assert client_b.post(
        f"/api/v1/learning/sessions/{session_id}/answers",
        headers=_csrf(client_b),
        json={
            "session_exercise_id": exercise["id"],
            "selected_option_id": exercise["options"][0]["id"],
            "idempotency_key": str(uuid4()),
        },
    ).status_code == 404
    assert client_b.post(
        f"/api/v1/learning/sessions/{session_id}/complete",
        headers=_csrf(client_b),
    ).status_code == 404
    assert client_b.post(
        f"/api/v1/learning/sessions/{session_id}/abandon",
        headers=_csrf(client_b),
    ).status_code == 404
    assert client_b.get("/api/v1/learning/progress").json()["items"] == []

    monkeypatch.setattr(
        "app.services.draft_preview.get_settings",
        lambda: Settings(_env_file=None, APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=False),
    )
    assert client_a.get(f"/api/v1/learning/sessions/{session_id}").status_code == 404
    hidden_sessions = client_a.get("/api/v1/learning/sessions")
    assert hidden_sessions.status_code == 200
    assert hidden_sessions.json()["items"] == []
    assert hidden_sessions.json()["total"] == 0
    hidden_progress = client_a.get("/api/v1/learning/progress")
    assert hidden_progress.status_code == 200
    assert hidden_progress.json()["items"] == []
    assert hidden_progress.json()["total"] == 0
    hidden_dashboard = client_a.get("/api/v1/learning/dashboard")
    assert hidden_dashboard.status_code == 200
    assert hidden_dashboard.json()["lessons_started"] == 0
    assert hidden_dashboard.json()["lessons_in_progress"] == 0
    assert hidden_dashboard.json()["active_sessions"] == []
    assert hidden_dashboard.json()["total_answered_exercises"] == 0
    assert hidden_dashboard.json()["recent_activity"] == []
    assert hidden_dashboard.json()["learning_path"] == []
    with sessions() as db:
        saved = db.get(LearningSession, UUID(session_id))
        assert saved is not None
        assert saved.status == "in_progress"
        assert db.scalar(select(func.count(LearningSession.id))) == 1
        assert db.scalar(select(func.count(ExerciseAttempt.id))) == 1
        assert db.scalar(select(func.count(LearningActivityEvent.id))) >= 1
