from uuid import UUID, uuid4
import pytest
from sqlalchemy import func, select
from app.ai.models import Conversation, Message
from app.models import User, UserSession
from app.privacy_models import AccountErasureJob
from app.services import account_privacy
from app.speech.models import AudioAsset, SpeechSession
from app.models import utcnow
from datetime import timedelta
from test_learning import PASSWORD, _csrf, _register_and_login
from test_interactive_learning import interactive, start
from app.services.email import get_email_service

BASE = "/api/v1/users/me"


def test_exports_are_reauthenticated_owned_paginated_and_key_free(interactive):
    client, sessions, lesson_id = interactive
    saved = start(client, lesson_id)
    with sessions.begin() as db:
        user = db.scalar(select(User).where(User.email == "interactive@example.com"))
        conversation = Conversation(user_id=user.id, title="My fictional conversation", mode="tutor", cefr_level="A1")
        db.add(conversation); db.flush()
        db.add_all([Message(conversation_id=conversation.id, role="user", content="Bonjour "+str(i)) for i in range(101)])
    assert client.post(BASE + "/data-export", json={"password": PASSWORD, "section": "messages"}).status_code == 403
    assert client.post(BASE + "/data-export", headers=_csrf(client), content="x"*4097).status_code == 413
    assert client.post(BASE + "/data-export", headers=_csrf(client), json={"password": "wrong", "section": "messages"}).status_code == 403
    response = client.post(BASE + "/data-export", headers=_csrf(client), json={"password": PASSWORD, "section": "messages"})
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    assert len(response.json()["items"]) == 100 and response.json()["next_offset"] == 100
    assert len(client.post(BASE + "/data-export", headers=_csrf(client), json={"password": PASSWORD, "section": "messages", "offset": 100}).json()["items"]) == 1
    assert client.post(BASE + "/data-export", headers=_csrf(client), json={"password": PASSWORD, "section": "users"}).status_code == 422
    for section in client.get(BASE + "/data-export").json()["sections"]:
        result = client.post(BASE + "/data-export", headers=_csrf(client), json={"password": PASSWORD, "section": section})
        assert result.status_code == 200, result.text
        for private_field in ("correct_option_id", "accepted_answers", "password_hash", "token_hash", "storage_key", "exercise_snapshot"):
            assert private_field not in result.text
    client.cookies.clear()
    _register_and_login(client, client.app.dependency_overrides[get_email_service](), "privacy-other@example.com")
    result = client.post(BASE + "/data-export", headers=_csrf(client), json={"password": PASSWORD, "section": "messages"})
    assert result.json()["items"] == []


def test_permanent_deletion_is_owned_and_audio_retries_survive_storage_failure(api_client, monkeypatch, tmp_path):
    client, sessions, emails = api_client
    _register_and_login(client, emails, "keep@example.com")
    with sessions() as db:
        keep = db.scalar(select(User.id).where(User.email == "keep@example.com"))
    client.cookies.clear()
    _register_and_login(client, emails, "erase@example.com")
    key = uuid4().hex + ".audio"
    with sessions.begin() as db:
        user = db.scalar(select(User).where(User.email == "erase@example.com")); uid = user.id
        conversation = Conversation(user_id=uid, title="Private", mode="tutor", cefr_level="A1")
        db.add(conversation); db.flush()
        speech = SpeechSession(user_id=uid, ai_conversation_id=conversation.id, cefr_level="A1")
        db.add(speech); db.flush()
        db.add(AudioAsset(owner_user_id=uid, speech_session_id=speech.id, storage_key=key, media_type="audio/wav",
            codec="pcm_s16le", duration_ms=1000, byte_size=3, checksum="a"*64, source_type="tutor",
            retention_expires_at=utcnow()+timedelta(hours=1)))
    real_file = tmp_path/key; real_file.write_bytes(b"wav")
    class FailingFile:
        def unlink(self, **kwargs): raise OSError("simulated storage outage")
    monkeypatch.setattr(account_privacy, "path_for", lambda _: FailingFile())
    payload = dict(password=PASSWORD, confirmation="DELETE MY ACCOUNT")
    assert client.post(BASE+"/delete-account", json=payload).status_code == 403
    assert client.post(BASE+"/delete-account", headers=_csrf(client), json={**payload, "password": "wrong"}).status_code == 403
    assert client.post(BASE+"/delete-account", headers=_csrf(client), json={**payload, "confirmation": "yes"}).status_code == 422
    assert client.post(BASE+"/delete-account", headers=_csrf(client), json={**payload, "user_id": str(keep)}).status_code == 422
    deleted = client.post(BASE+"/delete-account", headers=_csrf(client), json=payload)
    assert deleted.status_code == 202, deleted.text
    assert client.get("/api/v1/auth/me").status_code == 401
    with sessions() as db:
        assert db.get(User, uid) is None and db.get(User, keep) is not None
        assert db.scalar(select(func.count()).select_from(UserSession).where(UserSession.user_id==uid)) == 0
        assert db.scalar(select(func.count()).select_from(Conversation).where(Conversation.user_id==uid)) == 0
        job = db.get(AccountErasureJob, UUID(deleted.json()["receipt"]))
        assert job.account_reference == uid
        assert job.completed_at is None and job.storage_keys == [key]
        monkeypatch.setattr(account_privacy, "path_for", lambda _: real_file)
        account_privacy.cleanup_erasure_jobs(db)
        assert not real_file.exists() and job.completed_at is not None and job.storage_keys == []
        account_privacy.cleanup_erasure_jobs(db)  # Retry is idempotent.
        job.completed_at = utcnow()-timedelta(days=91)
        db.commit()
        account_privacy.cleanup_erasure_jobs(db)
        assert db.scalar(select(func.count()).select_from(AccountErasureJob)) == 0


def test_deletion_database_failure_rolls_back_without_touching_audio(api_client, monkeypatch):
    client, sessions, emails = api_client
    _register_and_login(client, emails, "rollback@example.com")
    with sessions() as db:
        user = db.scalar(select(User).where(User.email == "rollback@example.com")); uid = user.id
        def fail(): raise RuntimeError("synthetic commit failure")
        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(RuntimeError): account_privacy.erase(db, user)
        db.rollback()
    with sessions() as db:
        assert db.get(User, uid) is not None
        assert db.scalar(select(func.count()).select_from(AccountErasureJob)) == 0
