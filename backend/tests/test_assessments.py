"""Assessment API regressions using disposable SQLite and the real grader."""
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.learning_models import ExerciseAttempt, LearningSessionExercise, LessonProgress
from app.services.email import get_email_service
from test_interactive_learning import interactive, answer_for
from test_learning import _csrf, _register_and_login, _set_role

BASE = "/api/v1/learning/assessments"


def begin(client, lesson_id, skill="grammar"):
    response = client.post(BASE + "/sessions", headers=_csrf(client), json={
        "skill": skill, "lesson_id": lesson_id,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_assessment_catalog_start_completion_and_saved_evidence(interactive):
    client, sessions, lesson_id = interactive
    catalog = client.get(BASE).json()
    assert catalog["level"] == "A1" and catalog["draft_preview"] is True
    assert {item["skill"] for item in catalog["items"]} == {"grammar", "listening"}
    assert not any(key in str(catalog) for key in ("accepted_answers", "correct_option_id"))
    session = begin(client, lesson_id)
    assert session["activity_key"] == "assessment:grammar:objective-v1"
    assert begin(client, lesson_id)["id"] == session["id"]
    assert client.get(BASE + "/insights").json()["skills"][0]["percentage"] is None
    for exercise in session["exercises"]:
        with sessions() as db:
            frozen = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
        payload = dict(session_exercise_id=exercise["id"], idempotency_key=str(uuid4()), **answer_for(frozen))
        path = f"/api/v1/learning/sessions/{session['id']}/answers"
        first = client.post(path, headers=_csrf(client), json=payload)
        assert first.status_code == 200 and first.json()["is_correct"]
        retry = client.post(path, headers=_csrf(client), json=payload)
        assert retry.json()["idempotent_replay"]
    complete = client.post(f"/api/v1/learning/sessions/{session['id']}/complete", headers=_csrf(client))
    assert complete.status_code == 200 and complete.json()["percentage"] == 100
    assert client.post(f"/api/v1/learning/sessions/{session['id']}/complete", headers=_csrf(client)).json() == complete.json()
    history = client.get(BASE + "/history").json()
    assert history["items"][0]["status"] == "completed"
    assert history["items"][0]["answered"] == len(session["exercises"])
    evidence = client.get(BASE + "/insights").json()["skills"][0]
    assert evidence["percentage"] == 100 and evidence["completed_sessions"] == 1
    with sessions() as db:
        assert db.scalar(select(func.count(LessonProgress.id))) == 0
        assert db.scalar(select(func.count(ExerciseAttempt.id))) == len(session["exercises"])


def test_draft_denial_in_catalog_history_insights_and_existing_sessions(interactive):
    client, sessions, lesson_id = interactive
    session = begin(client, lesson_id, "listening")
    _set_role(sessions, "interactive@example.com", "learner")
    assert client.get(BASE).json()["items"] == []
    assert client.get(BASE + "/history").json()["items"] == []
    assert all(item["percentage"] is None for item in client.get(BASE + "/insights").json()["skills"])
    assert client.post(BASE + "/sessions", headers=_csrf(client), json={
        "skill": "listening", "lesson_id": lesson_id,
    }).status_code == 404
    assert client.get(f"/api/v1/learning/sessions/{session['id']}").status_code == 404


def test_saved_level_input_validation_and_ownership(interactive):
    client, sessions, lesson_id = interactive
    own = begin(client, lesson_id)
    assert client.get(BASE + "/history?limit=0").status_code == 422
    assert client.get(BASE + "/history?offset=-1").status_code == 422
    assert client.get(BASE + "/history?offset=100001").status_code == 422
    for body in (
        {"skill": "writing", "lesson_id": lesson_id},
        {"skill": "grammar", "lesson_id": "invalid"},
        {"skill": "grammar", "lesson_id": lesson_id, "level": "C2"},
    ):
        assert client.post(BASE + "/sessions", headers=_csrf(client), json=body).status_code == 422
    assert client.patch("/api/v1/users/me/preferences", headers=_csrf(client), json={"current_level": "a2"}).status_code == 200
    assert client.get(BASE).json()["items"] == []
    assert client.post(BASE + "/sessions", headers=_csrf(client), json={
        "skill": "grammar", "lesson_id": lesson_id,
    }).status_code == 404
    client.cookies.clear()
    assert client.get(BASE).status_code == 401
    emails = client.app.dependency_overrides[get_email_service]()
    _register_and_login(client, emails, "assessment-other@example.com")
    assert client.get(BASE + "/history").json()["items"] == []
    assert client.get(f"/api/v1/learning/sessions/{own['id']}").status_code == 404


def test_assessment_mistake_reuses_existing_planner_csrf_and_rate_limits(interactive):
    client, sessions, lesson_id = interactive
    session = begin(client, lesson_id)
    first = session["exercises"][0]
    with sessions() as db:
        frozen = db.get(LearningSessionExercise, UUID(first["id"])).exercise_snapshot
    wrong = next(option["id"] for option in frozen["options"] if option["id"] != frozen["correct_option_id"])
    assert client.post(f"/api/v1/learning/sessions/{session['id']}/answers", headers=_csrf(client), json={
        "session_exercise_id": first["id"], "selected_option_id": wrong, "idempotency_key": str(uuid4()),
    }).json()["is_correct"] is False
    recommendations = client.get("/api/v1/study/recommendations")
    assert recommendations.status_code == 200
    assert any(item["evidence_attempt_ids"] for item in recommendations.json())
    assert client.post(BASE + "/sessions", json={"skill": "grammar", "lesson_id": lesson_id}).status_code == 403
    for _ in range(19):
        assert client.post(BASE + "/sessions", headers=_csrf(client), json={
            "skill": "grammar", "lesson_id": lesson_id,
        }).status_code == 200
    limited = client.post(BASE + "/sessions", headers=_csrf(client), json={
        "skill": "grammar", "lesson_id": lesson_id,
    })
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
