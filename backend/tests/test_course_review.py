from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.config import ReviewGrant, Settings
from app.curriculum_models import Course, Exercise, Lesson, LessonGrammar, LessonObjective
from app.learning_models import LearningSessionExercise
from app.models import User, utcnow
from app.publish_content import publish_course
from test_curriculum import _approved_test_review_record, _import, _login, _publish_a1
from test_interactive_learning import answer_for
from test_learning import _csrf, _set_role


def test_independent_review_permissions_history_and_content_drift(api_client, monkeypatch):
    client, sessions, emails = api_client
    _import(sessions)
    _login(client, emails, sessions, "reviewer@example.com")
    with sessions() as db:
        user_id = db.scalar(select(User.id).where(User.email == "reviewer@example.com"))
        slug = db.scalar(select(Course.slug).where(Course.level_id == "A1"))
    base = "/api/v1/content-review"
    assert client.get(f"{base}/queue").status_code == 403
    settings = Settings(_env_file=None, CURRICULUM_REVIEWER_GRANTS={
        user_id: ReviewGrant(categories={"linguistic_accuracy"}, qualification="Synthetic qualification fixture")
    })
    monkeypatch.setattr("app.api.v1.content_review.get_settings", lambda: settings)
    queue = client.get(f"{base}/queue")
    assert queue.status_code == 200 and len(queue.json()["items"][0]["outstanding"]) == 5
    detail = client.get(f"{base}/{slug}").json()
    assert not detail["technical_issues"]
    payload = dict(version=detail["content"]["version"], digest=detail["digest"],
                   category="linguistic_accuracy", status="approved", findings="Synthetic review finding.")
    route = f"{base}/{slug}/decisions"
    assert client.post(route, json=payload).status_code == 403
    assert client.post(route, headers=_csrf(client), json={**payload, "category": "phonetics"}).status_code == 403
    assert client.post(route, headers=_csrf(client), json=payload).status_code == 201
    changed = {**payload, "status": "changes_requested", "required_corrections": "Check the new phrasing."}
    assert client.post(route, headers=_csrf(client), json=changed).status_code == 201
    detail = client.get(f"{base}/{slug}").json()
    assert len(detail["history"]) == 2
    assert "linguistic_accuracy" in detail["readiness"]["outstanding"]
    with sessions.begin() as db:
        exercise = db.scalar(select(Exercise).join(Lesson).where(Lesson.slug == "a1-001"))
        exercise.prompt += " Revised prompt."
    assert client.post(route, headers=_csrf(client), json=payload).status_code == 409
    assert len(client.get(f"{base}/{slug}").json()["history"]) == 2
    _set_role(sessions, "reviewer@example.com", "admin")
    assert client.post(route, headers=_csrf(client), json=payload).status_code == 403


def test_published_learner_journey_uses_only_synthetic_review_fixtures(api_client):
    client, sessions, emails = api_client
    _import(sessions)
    with sessions.begin() as db:
        db.add(User(id=UUID(int=1), email="publication-test-admin@example.com",
                    password_hash="not-a-login-fixture", role="admin", email_verified_at=utcnow()))
        lesson = db.scalar(select(Lesson).where(Lesson.slug == "a1-001"))
        exercise = db.scalar(select(Exercise).where(Exercise.lesson_id == lesson.id).order_by(Exercise.sequence_order))
        topic = db.scalar(select(LessonGrammar.grammar_topic_id).where(LessonGrammar.lesson_id == lesson.id))
        exercise.grammar_topic_id = topic
        exercise.learning_objective_id = db.scalar(select(LessonObjective.objective_id)
            .where(LessonObjective.lesson_id == lesson.id))
        lid = str(lesson.id)
    with sessions.begin() as db, pytest.raises(ValueError, match="five current independent reviews"):
        publish_course(db, _approved_test_review_record())
    _login(client, emails, sessions, "published-journey@example.com")
    assert client.get(f"/api/v1/lessons/{lid}").status_code == 404
    _publish_a1(sessions)
    assert client.patch("/api/v1/users/me/preferences", headers=_csrf(client),
                        json={"current_level": "a1", "daily_study_minutes": 15}).status_code == 200
    plan = client.post("/api/v1/study/today/generate", headers=_csrf(client), json={"request_id": str(uuid4())})
    assert plan.status_code == 200
    assert client.get(f"/api/v1/lessons/{lid}").status_code == 200
    start = client.post("/api/v1/learning/sessions", headers=_csrf(client), json={"lesson_id": lid})
    assert start.status_code == 201 and not start.json()["preview_mode"]
    lesson_session = start.json()
    for question in lesson_session["exercises"]:
        sid = lesson_session["id"]
        with sessions() as db:
            frozen = db.get(LearningSessionExercise, UUID(question["id"])).exercise_snapshot
        answer = answer_for(frozen)
        if question["exercise_order"] == 1:
            answer["selected_option_id"] = next(option["id"] for option in question["options"]
                                                if option["id"] != answer["selected_option_id"])
        assert client.post(f"/api/v1/learning/sessions/{sid}/answers", headers=_csrf(client), json={
            "session_exercise_id": question["id"], "idempotency_key": str(uuid4()), **answer}).status_code == 200
        assert client.get(f"/api/v1/learning/sessions/{sid}").json()["answered_exercises"] == question["exercise_order"]
    assert client.post(f"/api/v1/learning/sessions/{sid}/complete", headers=_csrf(client)).status_code == 200
    assert client.get(f"/api/v1/learning/sessions/{sid}/results").json()["incorrect_answers"] == 1
    mistake = client.get("/api/v1/learning/mistakes?level=A1").json()["items"][0]
    retry = client.post("/api/v1/learning/practice/sessions", headers=_csrf(client), json={
        "category": "mistakes", "attempt_id": mistake["attempt_id"]})
    assert retry.status_code == 200 and len(retry.json()["exercises"]) == 1
    grammar = client.get("/api/v1/learning/grammar?level=A1").json()["items"]
    assert next(entry for entry in grammar if entry["id"] == str(topic))["recent_mistakes"] == 1
    practice = client.post("/api/v1/learning/practice/sessions", headers=_csrf(client), json={
        "category": "grammar", "grammar_topic_id": str(topic)})
    assert practice.status_code == 200 and len(practice.json()["exercises"]) == 1
    focused = practice.json()
    with sessions() as db:
        answer = answer_for(db.get(LearningSessionExercise, UUID(focused["exercises"][0]["id"])).exercise_snapshot)
    assert client.post(f"/api/v1/learning/sessions/{focused['id']}/answers", headers=_csrf(client), json={
        "session_exercise_id": focused["exercises"][0]["id"], "idempotency_key": str(uuid4()), **answer}).status_code == 200
    assert client.post(f"/api/v1/learning/sessions/{focused['id']}/complete", headers=_csrf(client)).status_code == 200
    grammar = client.get("/api/v1/learning/grammar?level=A1").json()["items"]
    assert next(entry for entry in grammar if entry["id"] == str(topic))["recent_correct"] == 1
    assert client.get("/api/v1/learning/mistakes?level=A1").json()["items"] == []
    assert client.get(f"/api/v1/learning/progress/lessons/{lid}").json()["completion_count"] == 1
    assert client.post(f"/api/v1/learning/lessons/{lid}/tutor", headers=_csrf(client)).status_code == 200
    assert client.post(f"/api/v1/learning/lessons/{lid}/speaking", headers=_csrf(client)).status_code == 200
    _login(client, emails, sessions, "another-published-learner@example.com")
    assert client.get(f"/api/v1/learning/sessions/{sid}/results").status_code == 404
    assert client.post("/api/v1/learning/practice/sessions", headers=_csrf(client), json={
        "category": "mistakes", "attempt_id": mistake["attempt_id"]}).status_code == 404
