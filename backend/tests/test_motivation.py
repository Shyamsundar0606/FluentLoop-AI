from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.curriculum_models import Lesson
from app.learning_models import LearningSession, LearningSessionExercise
from app.models import User
from app.services.motivation_service import streaks
from app.services.study_clock import study_date
from app.study_models import LearningAchievement, LearningReward
from test_curriculum import _publish_a1
from test_learning import _csrf, _import_content, _register_and_login
from test_interactive_learning import interactive, start, answer_for


def complete_lesson(client, sessions, lesson_id):
    started = client.post("/api/v1/learning/sessions", headers=_csrf(client), json={"lesson_id": str(lesson_id)})
    assert started.status_code == 201, started.text
    session = started.json()
    for exercise in session["exercises"]:
        with sessions() as db:
            saved = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
        assert client.post(f"/api/v1/learning/sessions/{session['id']}/answers", headers=_csrf(client), json={
            "session_exercise_id": exercise["id"], "selected_option_id": saved["correct_option_id"],
            "idempotency_key": str(uuid4()),
        }).status_code == 200
    assert client.post(f"/api/v1/learning/sessions/{session['id']}/complete", headers=_csrf(client)).status_code == 200
    return UUID(session["id"])


def test_rewards_are_idempotent_optional_and_owned(api_client, monkeypatch):
    client, sessions, emails = api_client
    _register_and_login(client, emails, "motivation@example.com")
    _import_content(sessions)
    _publish_a1(sessions)
    with sessions() as db:
        lid = db.scalar(select(Lesson.id).where(Lesson.slug == "a1-001"))
    sid = complete_lesson(client, sessions, lid)
    with sessions.begin() as db:
        user = db.scalar(select(User).where(User.email == "motivation@example.com"))
        user.profile.timezone = "Europe/Paris"
        db.get(LearningSession, sid).completed_at = datetime(2026, 11, 3, 23, 30, tzinfo=timezone.utc)
    monkeypatch.setattr("app.services.motivation_service.clock.now", lambda: datetime(2026, 11, 4, 12, tzinfo=timezone.utc))
    path = "/api/v1/study/motivation"
    assert client.post(path + "/sync").status_code == 403
    first = client.post(path + "/sync", headers=_csrf(client))
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["total_xp"] == 20 and result["today_activities"] == 1
    assert result["current_streak"] == 1
    assert any(item["key"] == "first_lesson" for item in result["achievements"])
    assert client.post(path + "/sync", headers=_csrf(client)).json()["total_xp"] == 20
    assert client.get(path + "/history").json()["items"][0]["study_date"] == "2026-11-04"
    assert client.patch("/api/v1/users/me/preferences", headers=_csrf(client), json={"motivation_enabled": False}).status_code == 200
    assert client.post(path + "/sync", headers=_csrf(client)).json()["enabled"] is False
    with sessions() as db:
        assert db.scalar(select(func.count(LearningReward.id))) == 1
        assert db.scalar(select(func.count(LearningAchievement.id))) == 1
    client.cookies.clear()
    _register_and_login(client, emails, "motivation-other@example.com")
    assert client.get(path).json()["total_xp"] == 0
    assert client.get(path + "/history").json()["items"] == []


def test_calendar_streaks_handle_missing_days_and_day_boundaries():
    today = date(2026, 11, 4)
    assert streaks([], today) == (0, 0)
    assert streaks([date(2026, 11, 2), date(2026, 11, 3), today, today], today) == (3, 3)
    assert streaks([date(2026, 11, 1), date(2026, 11, 2)], today) == (0, 2)
    assert streaks([date(2026, 11, 2), date(2026, 11, 3)], today) == (2, 2)
    before, _ = study_date(datetime(2026, 3, 28, 23, 30, tzinfo=timezone.utc), "Europe/Paris")
    after, _ = study_date(datetime(2026, 3, 29, 22, 30, tzinfo=timezone.utc), "Europe/Paris")
    assert before == date(2026, 3, 29) and after == date(2026, 3, 30)


def test_draft_preview_completions_do_not_earn_rewards(interactive):
    client, sessions, lesson_id = interactive
    session = start(client, lesson_id)
    for exercise in session["exercises"]:
        with sessions() as db:
            saved = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
        assert client.post(f"/api/v1/learning/sessions/{session['id']}/answers", headers=_csrf(client), json={
            "session_exercise_id": exercise["id"], "idempotency_key": str(uuid4()), **answer_for(saved),
        }).status_code == 200
    assert client.post(f"/api/v1/learning/sessions/{session['id']}/complete", headers=_csrf(client)).status_code == 200
    assert client.post("/api/v1/study/motivation/sync", headers=_csrf(client)).json()["total_xp"] == 0
