"""Personal preview is learning-only, revocable and isolated in disposable SQLite."""
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.config import Settings
from app.curriculum_models import Course, Lesson
from app.learning_models import LearningSession, LearningSessionExercise
from app.models import User
from app.services.draft_preview import can_author_drafts, can_preview_drafts
from test_interactive_learning import interactive, start, answer_for
from test_learning import _csrf, _register_and_login
from app.services.email import get_email_service


def grant(interactive, monkeypatch, **overrides):
    client, sessions, lid = interactive
    with sessions.begin() as db:
        user = db.scalar(select(User).where(User.email == "interactive@example.com"))
        user.role = "learner"
        uid = user.id
    values = dict(APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=False,
                  ENABLE_PERSONAL_LEARNING_PREVIEW=True, PERSONAL_PREVIEW_USER_IDS=[uid])
    values.update(overrides)
    settings = Settings(_env_file=None, **values)
    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: settings)
    return uid, settings


def test_personal_learner_completes_all_formats_without_authoring(interactive, monkeypatch):
    client, sessions, lid = interactive
    uid, _ = grant(interactive, monkeypatch)
    assert client.get("/api/v1/learning/access").json()["mode"] == "draft_preview"
    assert client.get("/api/v1/learning/grammar").json()["items"]
    saved = start(client, lid)
    assert saved["preview_mode"] is True
    assert len({e["type"] for e in saved["exercises"]}) == 6
    assert "correct_option_id" not in str(saved)
    for exercise in saved["exercises"]:
        with sessions() as db:
            frozen = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
        payload = dict(session_exercise_id=exercise["id"], idempotency_key=str(uuid4()), **answer_for(frozen))
        result = client.post(f"/api/v1/learning/sessions/{saved['id']}/answers", headers=_csrf(client), json=payload)
        assert result.status_code == 200, result.text
        assert result.json()["is_correct"]
    assert client.post(f"/api/v1/learning/sessions/{saved['id']}/complete", headers=_csrf(client)).status_code == 200
    assert client.get(f"/api/v1/learning/sessions/{saved['id']}").status_code == 200
    assert client.post("/api/v1/study/motivation/sync", headers=_csrf(client)).json()["total_xp"] == 0
    assert client.get("/api/v1/auth/me").json()["user"]["role"] == "learner"
    for path in ("/api/v1/content-review/queue", "/api/v1/content-review/anything"):
        assert client.get(path).status_code == 403
    assert client.post("/api/v1/content-review/anything/revisions", headers=_csrf(client)).status_code == 403
    assert client.post("/api/v1/content-review/anything/decisions", headers=_csrf(client), json={
        "version": "0.1.0", "digest": "a" * 64, "category": "pedagogy",
        "status": "approved", "findings": "Disposable decision denied.",
    }).status_code == 403
    with sessions() as db:
        assert db.get(User, uid).role == "learner"
        assert not can_author_drafts(db.get(User, uid))
        assert db.get(LearningSession, UUID(saved["id"])).preview_mode
        assert db.get(Lesson, UUID(lid)).status == "draft"
        assert all(c.status != "published" for c in db.scalars(select(Course)))


@pytest.mark.parametrize("overrides", [
    {"APP_ENV": "production", "COOKIE_SECURE": True},
    {"ENABLE_PERSONAL_LEARNING_PREVIEW": False},
    {"PERSONAL_PREVIEW_USER_IDS": []},
    {"FRONTEND_ORIGIN": "https://example.com", "CORS_ORIGINS": ["https://example.com"]},
])
def test_personal_grant_fails_closed(interactive, monkeypatch, overrides):
    client, _, lid = interactive
    grant(interactive, monkeypatch, **overrides)
    assert client.get("/api/v1/learning/access").json()["mode"] == "published_only"
    assert client.post("/api/v1/learning/sessions", headers=_csrf(client), json={"lesson_id": lid}).status_code == 404


def test_revocation_retains_frozen_session_and_answers(interactive, monkeypatch):
    client, sessions, lid = interactive
    uid, settings = grant(interactive, monkeypatch)
    saved = start(client, lid)
    exercise = saved["exercises"][0]
    with sessions() as db:
        snapshot = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
    response = client.post(f"/api/v1/learning/sessions/{saved['id']}/answers", headers=_csrf(client),
        json=dict(session_exercise_id=exercise["id"], idempotency_key=str(uuid4()), **answer_for(snapshot)))
    assert response.status_code == 200
    settings.personal_preview_user_ids = set()
    assert client.get(f"/api/v1/learning/sessions/{saved['id']}").status_code == 404
    assert client.post(f"/api/v1/learning/sessions/{saved['id']}/resume", headers=_csrf(client)).status_code == 404
    assert client.post(f"/api/v1/learning/sessions/{saved['id']}/exercises/{exercise['id']}/audio", headers=_csrf(client)).status_code == 404
    with sessions() as db:
        assert db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot == snapshot
    settings.personal_preview_user_ids = {uid}
    resumed = client.get(f"/api/v1/learning/sessions/{saved['id']}")
    assert resumed.status_code == 200 and resumed.json()["answered_exercises"] == 1


def test_other_account_cannot_use_grant_or_session(interactive, monkeypatch):
    client, sessions, lid = interactive
    grant(interactive, monkeypatch)
    saved = start(client, lid)
    _register_and_login(client, client.app.dependency_overrides[get_email_service](), "other-personal@example.com")
    assert client.get("/api/v1/learning/access").json()["mode"] == "published_only"
    assert client.get(f"/api/v1/learning/sessions/{saved['id']}").status_code == 404
    assert client.post("/api/v1/learning/sessions", headers=_csrf(client), json={"lesson_id": lid}).status_code == 404


def test_unverified_inactive_and_unlisted_users_denied(monkeypatch):
    uid = uuid4()
    settings = Settings(_env_file=None, APP_ENV="development", ENABLE_PERSONAL_LEARNING_PREVIEW=True, PERSONAL_PREVIEW_USER_IDS=[uid])
    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: settings)
    user = User(id=uid, role="learner", is_active=True)
    assert not can_preview_drafts(user)
    from app.security import utcnow
    user.email_verified_at = utcnow()
    assert can_preview_drafts(user)
    user.is_active = False
    assert not can_preview_drafts(user)


def test_uuid_setting_rejects_email_and_defaults_off():
    assert not Settings(_env_file=None).personal_learning_preview_enabled
    with pytest.raises(ValueError):
        Settings(_env_file=None, PERSONAL_PREVIEW_USER_IDS=["learner@example.com"])


def test_personal_assessment_and_vocabulary_catalog(interactive, monkeypatch):
    client, _, lid = interactive
    _, settings = grant(interactive, monkeypatch)
    catalog = client.get("/api/v1/learning/assessments").json()
    assert catalog["draft_preview"] and catalog["items"]
    response = client.post("/api/v1/learning/assessments/sessions", headers=_csrf(client),
                           json={"skill": "grammar", "lesson_id": lid})
    assert response.status_code == 200 and response.json()["preview_mode"]
    assert client.get("/api/v1/review/due").status_code == 200
    settings.personal_preview_user_ids = set()
    assert client.get("/api/v1/learning/assessments/history").json()["items"] == []


def test_personal_draft_tutor_voice_and_history_revoke_together(interactive, monkeypatch, tmp_path):
    from app.api.v1.ai import provider_dependency
    from app.config import get_settings
    from app.speech.providers import get_speech_provider
    from test_speech import FakeSpeech, FakeTutor, upload

    client, _, lid = interactive
    _, settings = grant(interactive, monkeypatch)
    client.app.dependency_overrides[provider_dependency] = lambda: FakeTutor()
    client.app.dependency_overrides[get_speech_provider] = lambda: FakeSpeech()
    monkeypatch.setattr(get_settings(), "speech_storage_path", str(tmp_path))
    result = client.post("/api/v1/ai/conversations", headers=_csrf(client), json={"linked_lesson_id": lid})
    assert result.status_code == 201 and result.json()["preview_mode"]
    cid = result.json()["id"]
    assert client.post(f"/api/v1/ai/conversations/{cid}/messages", headers=_csrf(client),
                       json={"message": "Bonjour !", "request_id": str(uuid4())}).status_code == 200
    result = client.post("/api/v1/speech/sessions", headers=_csrf(client), json={"conversation_id": cid})
    assert result.status_code == 201
    sid = result.json()["id"]
    turn = upload(client, sid)
    assert turn.status_code == 200, turn.text
    assert turn.json()["transcript"].startswith("Bonjour")
    assert turn.json()["tutor_audio"]["status"] == "ready"
    history = client.get(f"/api/v1/speech/sessions/{sid}/history")
    assert history.status_code == 200
    settings.personal_preview_user_ids = set()
    assert client.get(f"/api/v1/ai/conversations/{cid}").status_code == 404
    assert client.get(f"/api/v1/speech/sessions/{sid}/history").status_code == 404
