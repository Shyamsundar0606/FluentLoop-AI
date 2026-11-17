import os
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from app.curriculum_models import Lesson
from app.learning_models import LearningSessionExercise
from app.models import User, UserPreferences, UserProfile, utcnow
from app.services import learning_service, motivation_service
from app.study_models import LearningReward
from test_curriculum import _publish_a1
from test_interactive_postgres import database, migrate
from test_learning import _import_content

pytestmark = pytest.mark.skipif(not os.getenv("M08_TEST_ADMIN_DATABASE_URL"),
                               reason="Requires disposable PostgreSQL reward database.")


def test_concurrent_reward_sync_is_unique_and_rollback_preserves_it(database):
    url, engine = database
    migrate(url, "head")
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    _import_content(sessions)
    _publish_a1(sessions)
    with sessions.begin() as db:
        user = User(email="reward-concurrency@example.com", role="learner", password_hash="unused-test-only", email_verified_at=utcnow())
        db.add(user)
        db.flush()
        uid = user.id
        db.add(UserPreferences(user_id=uid))
        db.add(UserProfile(user_id=uid, display_name="Synthetic reward learner", timezone="Europe/Paris"))
    with sessions() as db:
        user = db.get(User, uid)
        lid = db.scalar(select(Lesson.id).where(Lesson.slug == "a1-001"))
        session, _ = learning_service.start_session(db, user=user, lesson_id=lid)
        for exercise in session.exercises:
            frozen = db.get(LearningSessionExercise, exercise.id).exercise_snapshot
            learning_service.submit_answer(db, user=user, session_id=session.id, session_exercise_id=exercise.id,
                selected_option_id=UUID(frozen["correct_option_id"]), idempotency_key=uuid4())
        learning_service.complete_session(db, user=user, session_id=session.id)

    def sync():
        with sessions() as db:
            return motivation_service.sync(db, db.get(User, uid))["total_xp"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: sync(), range(2))) == [20, 20]
    with sessions() as db:
        assert db.scalar(select(func.count(LearningReward.id))) == 1
    with engine.connect() as db:
        prior_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    migrate(url, "20261115_0012", success=False, downgrade=True)
    with engine.connect() as db:
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == prior_revision
