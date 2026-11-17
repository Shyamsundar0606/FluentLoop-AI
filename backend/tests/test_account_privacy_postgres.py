import os
from uuid import UUID, uuid4
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from app.models import User, UserProfile, UserPreferences, utcnow
from app.learning_models import LearningSessionExercise, WritingSubmission
from app.curriculum_models import Lesson
from app.services import account_privacy, learning_service, motivation_service
from app.privacy_models import AccountErasureJob
from test_interactive_postgres import database, migrate
from test_learning import _import_content
from test_curriculum import _publish_a1

pytestmark = pytest.mark.skipif(not os.getenv("M08_TEST_ADMIN_DATABASE_URL"), reason="Requires dedicated disposable PostgreSQL.")


def test_postgres_erasure_removes_history_preserves_other_users_and_guards_rollback(database):
    url, engine = database
    migrate(url, "head")
    migrate(url, "20261115_0015", downgrade=True)
    migrate(url, "head")
    sessions = sessionmaker(bind=engine)
    _import_content(sessions); _publish_a1(sessions)
    with sessions.begin() as db:
        user = User(email="erase-pg@example.com", password_hash="synthetic-only", email_verified_at=utcnow())
        other = User(email="keep-pg@example.com", password_hash="synthetic-only")
        db.add_all([user, other]); db.flush(); uid, other_id = user.id, other.id
        db.add_all([UserProfile(user_id=uid, display_name="Synthetic"), UserPreferences(user_id=uid)])
    with sessions() as db:
        user = db.get(User, uid)
        lesson = db.scalar(select(Lesson).where(Lesson.slug=="a1-001"))
        saved, _ = learning_service.start_session(db, user=user, lesson_id=lesson.id)
        for exercise in saved.exercises:
            frozen = db.get(LearningSessionExercise, exercise.id).exercise_snapshot
            learning_service.submit_answer(db, user=user, session_id=saved.id, session_exercise_id=exercise.id,
                selected_option_id=UUID(frozen["correct_option_id"]), idempotency_key=uuid4())
        learning_service.complete_session(db, user=user, session_id=saved.id)
        motivation_service.sync(db, user)
        for owner in (uid, other_id):
            db.add(WritingSubmission(user_id=owner, lesson_id=lesson.id, idempotency_key=uuid4(), cefr_level="A1",
                lesson_content_version=lesson.content_version, prompt_snapshot="Private prompt, not exported",
                original_text="Je suis ici.", preview_mode=False))
        db.commit()
        receipt = account_privacy.erase(db, user)
        account_privacy.cleanup_erasure_jobs(db)
    with sessions() as db:
        assert db.get(User, uid) is None and db.get(User, other_id) is not None
        for name in ("learning_sessions", "exercise_attempts", "lesson_progress", "writing_submissions", "learning_rewards", "learning_achievements"):
            assert db.execute(text(f"SELECT count(*) FROM {name} WHERE user_id=:owner"), {"owner": uid}).scalar_one() == 0
        assert db.scalar(select(WritingSubmission).where(WritingSubmission.user_id==other_id)) is not None
        assert db.get(AccountErasureJob, receipt).completed_at is not None
        assert db.get(AccountErasureJob, receipt).account_reference == uid
        prior_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    migrate(url, "20261115_0014", success=False, downgrade=True)
    with engine.connect() as db:
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == prior_revision
