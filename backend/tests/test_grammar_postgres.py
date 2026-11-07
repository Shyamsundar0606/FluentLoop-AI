import os
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.curriculum_models import ExerciseOption, Lesson
from app.grammar_content import import_supplement, load_supplement
from app.interactive_content import import_pack, load_pack
from app.learning_models import LearningSessionExercise
from app.models import User, UserPreferences, utcnow
from app.security import hash_password
from app.services.learning_service import start_session
from test_interactive_postgres import database, migrate
from test_learning import _import_content

pytestmark = pytest.mark.skipif(
    not os.getenv("M08_TEST_ADMIN_DATABASE_URL"), reason="Requires a disposable local M08 PostgreSQL database."
)


def test_postgres_supplement_keeps_existing_versions_and_snapshot_keys(database, monkeypatch):
    url, engine = database
    migrate(url, "head")
    sessions = sessionmaker(bind=engine)
    _import_content(sessions)
    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: Settings(
        _env_file=None, APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=True))
    with sessions.begin() as db:
        import_pack(db, load_pack())
        fixture = db.scalar(select(Lesson).where(Lesson.slug == "m08-etre-interactive-lesson"))
        user = User(email="historical@example.com", role="admin",
                    password_hash=hash_password(uuid4().hex), email_verified_at=utcnow())
        db.add(user)
        db.flush()
        db.add(UserPreferences(user_id=user.id))
        user_id, fixture_id = user.id, fixture.id
    with sessions() as db:
        session, _ = start_session(db, user=db.get(User, user_id), lesson_id=fixture_id)

    with sessions.begin() as db:
        snapshots = select(LearningSessionExercise.id, LearningSessionExercise.exercise_snapshot).where(
            LearningSessionExercise.learning_session_id == session.id)
        before = dict(db.execute(snapshots).all())
        assert len(before) == 6
        versions = dict(db.execute(select(Lesson.id, Lesson.content_version)).all())
        answer_keys = dict(db.execute(select(ExerciseOption.id, ExerciseOption.is_correct)).all())
        pack = load_supplement()
        assert import_supplement(db, pack)["exercises"] == 25
        assert import_supplement(db, pack)["unchanged"]
        assert dict(db.execute(snapshots).all()) == before
        assert dict(db.execute(select(Lesson.id, Lesson.content_version).where(Lesson.id.in_(versions))).all()) == versions
        assert dict(db.execute(select(ExerciseOption.id, ExerciseOption.is_correct).where(
            ExerciseOption.id.in_(answer_keys))).all()) == answer_keys
