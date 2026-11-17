import os
import re
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.ai.models import Conversation, Message
from app.curriculum_models import Lesson
from app.learning_models import LearningSessionExercise, WritingSubmission
from app.models import User, UserPreferences, UserProfile, utcnow
from app.privacy_models import AccountErasureJob
from app.services import account_privacy, erasure_reconciliation, learning_service, motivation_service
from app.speech.models import AudioAsset, SpeechSession
from test_interactive_postgres import database, migrate
from test_learning import _import_content
from test_curriculum import _publish_a1

pytestmark = pytest.mark.skipif(not os.getenv("M08_TEST_ADMIN_DATABASE_URL"), reason="Requires dedicated disposable PostgreSQL.")


def test_restored_pre_erasure_database_replays_current_ledger_and_audio_safely(database, monkeypatch, tmp_path):
    url, engine = database
    migrate(url, "head")
    sessions = sessionmaker(bind=engine)
    _import_content(sessions); _publish_a1(sessions)  # Disposable test fixture only.
    source_audio, restored_audio = tmp_path/"source", tmp_path/"restored"
    source_audio.mkdir(); restored_audio.mkdir()
    from app.speech import storage
    config = storage.get_settings()
    monkeypatch.setattr(storage, "get_settings", lambda: config.model_copy(update={"speech_storage_path": str(source_audio)}))
    key = uuid4().hex+".audio"
    (source_audio/key).write_bytes(b"synthetic-audio")
    (restored_audio/key).write_bytes(b"synthetic-audio")
    with sessions.begin() as db:
        user = User(email="rc-erasure@example.com", password_hash="synthetic-only")
        other = User(email="rc-preserved@example.com", password_hash="synthetic-only")
        db.add_all([user, other]); db.flush(); uid, other_id = user.id, other.id
        db.add_all([UserProfile(user_id=uid, display_name="Synthetic erasure"), UserPreferences(user_id=uid)])
    with sessions() as db:
        user = db.get(User, uid); lesson = db.scalar(select(Lesson).where(Lesson.slug=="a1-001"))
        saved, _ = learning_service.start_session(db, user=user, lesson_id=lesson.id)
        for exercise in saved.exercises:
            frozen = db.get(LearningSessionExercise, exercise.id).exercise_snapshot
            learning_service.submit_answer(db, user=user, session_id=saved.id, session_exercise_id=exercise.id,
                selected_option_id=UUID(frozen["correct_option_id"]), idempotency_key=uuid4())
        learning_service.complete_session(db, user=user, session_id=saved.id)
        motivation_service.sync(db, user)
        conversation = Conversation(user_id=uid, title="Synthetic history", mode="tutor", cefr_level="A1")
        db.add(conversation); db.flush()
        db.add(Message(conversation_id=conversation.id, role="user", content="Bonjour."))
        speech = SpeechSession(user_id=uid, ai_conversation_id=conversation.id, cefr_level="A1")
        db.add(speech); db.flush()
        db.add(AudioAsset(owner_user_id=uid, speech_session_id=speech.id, storage_key=key, media_type="audio/wav",
            codec="pcm_s16le", duration_ms=1000, byte_size=15, checksum="a"*64, source_type="tutor",
            retention_expires_at=utcnow()+timedelta(hours=1)))
        for owner, original in [(uid, "Je suis ici."), (uid, "Je suis à Paris."), (other_id, "Preserved other user text.")]:
            db.add(WritingSubmission(user_id=owner, lesson_id=lesson.id, idempotency_key=uuid4(), cefr_level="A1",
                lesson_content_version=lesson.content_version, prompt_snapshot="Synthetic writing", original_text=original, preview_mode=False))
        db.commit()
        assert len(account_privacy.export_page(db, user, "writing", 0)["items"]) == 2
        assert len(account_privacy.export_page(db, user, "achievements", 0)["items"]) == 1
        assert "Preserved other user" not in str(account_privacy.export_page(db, user, "writing", 0))
    # A consistent database-template copy represents the pre-erasure snapshot.
    # Custom pg_dump/pg_restore and all-table fingerprints are verified separately.
    engine.dispose()
    parsed = make_url(url); source = parsed.database; target = "fluentloop_m08_rc_restore_"+uuid4().hex[:10]
    assert source.startswith("fluentloop_") and re.fullmatch(r"[a-z0-9_]+", source)
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    restored = None
    try:
        with admin.connect() as db: db.execute(text(f'CREATE DATABASE "{target}" TEMPLATE "{source}"'))
        restored = create_engine(parsed.set(database=target)); restored_sessions = sessionmaker(bind=restored)
        with sessions() as db:
            account_privacy.erase(db, db.get(User, uid))
            class InterruptedFile:
                def unlink(self, **kwargs): raise OSError("synthetic interruption")
            with monkeypatch.context() as patch:
                patch.setattr(account_privacy, "path_for", lambda _: InterruptedFile())
                account_privacy.cleanup_erasure_jobs(db)
            assert (source_audio/key).exists()
            assert db.scalar(select(AccountErasureJob)).completed_at is None
            account_privacy.cleanup_erasure_jobs(db)
            references = db.scalars(select(AccountErasureJob.account_reference)).all()
            assert not (source_audio/key).exists()
        monkeypatch.setattr(storage, "get_settings", lambda: config.model_copy(update={"speech_storage_path": str(restored_audio)}))
        with restored_sessions() as db:
            assert db.get(User, uid) is not None  # Restore must stay private here.
            assert erasure_reconciliation.replay(db, references) == {"references":1, "removed":1}
            assert erasure_reconciliation.replay(db, references) == {"references":1, "removed":0}
            account_privacy.cleanup_erasure_jobs(db)
            assert not (restored_audio/key).exists()
            assert db.get(User, uid) is None and db.get(User, other_id) is not None
            for name in ("learning_sessions", "exercise_attempts", "writing_submissions", "ai_conversations", "speech_sessions", "learning_rewards", "learning_achievements"):
                assert db.execute(text(f"SELECT count(*) FROM {name} WHERE user_id=:owner"), {"owner":uid}).scalar_one() == 0
            assert db.scalar(select(WritingSubmission.original_text).where(WritingSubmission.user_id==other_id)) == "Preserved other user text."
    finally:
        if restored is not None: restored.dispose()
        assert target.startswith("fluentloop_m08_rc_restore_")
        with admin.connect() as db: db.execute(text(f'DROP DATABASE IF EXISTS "{target}" WITH (FORCE)'))
        admin.dispose()
