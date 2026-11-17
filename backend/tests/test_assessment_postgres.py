"""Writing migration and frozen assessment checks in disposable PostgreSQL."""
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.api.v1.assessments import SubmitWriting
from app.assessment_content import import_assessment_pack, load_assessment_pack
from app.config import Settings
from app.curriculum_models import Lesson
from app.learning_models import WritingSubmission
from app.models import User, UserPreferences, utcnow
from app.services import assessment_service, writing_service
from test_interactive_postgres import database, migrate
from test_learning import _import_content

pytestmark = pytest.mark.skipif(not os.getenv("M08_TEST_ADMIN_DATABASE_URL"),
                               reason="Requires disposable PostgreSQL assessment database.")


def test_postgres_writing_upgrade_snapshots_and_guarded_downgrade(database, monkeypatch):
    url, engine = database
    migrate(url, "head")
    sessions = sessionmaker(bind=engine)
    _import_content(sessions)
    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: Settings(
        _env_file=None, APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=True))
    with sessions.begin() as db:
        import_assessment_pack(db, load_assessment_pack())
        user = User(email="assessment-migration@example.com", password_hash="unused-test-only",
                    role="admin", email_verified_at=utcnow())
        db.add(user)
        db.flush()
        db.add(UserPreferences(user_id=user.id))
        uid = user.id
    with sessions() as db:
        user = db.get(User, uid)
        lesson_id = db.scalar(select(Lesson.id).where(Lesson.slug.endswith("-introduce-yourself")))
        saved = writing_service.submit(db, user, SubmitWriting(lesson_id=lesson_id,
            idempotency_key=uuid4(), text="Je m'appelle Lina."))
        reading_id = db.scalar(select(Lesson.id).where(Lesson.slug.endswith("-message-from-lina")))
        reading = assessment_service.start(db, user, "reading", reading_id)
        assert "J'habite à Lyon" in reading.lesson["assessment_context"]
    migrate(url, "20261108_0010", success=False, downgrade=True)
    with sessions() as db:
        assert db.get(WritingSubmission, UUID(saved["id"])).original_text == "Je m'appelle Lina."
