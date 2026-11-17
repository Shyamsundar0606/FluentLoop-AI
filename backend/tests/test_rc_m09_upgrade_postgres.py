"""Explicit M09 -> RC upgrade and empty-feature rollback preservation."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker
from app.curriculum_models import Lesson
from app.learning_models import LearningSession, LearningSessionExercise, ExerciseAttempt
from app.models import User, UserPreferences, UserProfile, utcnow
from test_interactive_postgres import database, migrate
from test_learning import _import_content

pytestmark = pytest.mark.skipif(not os.getenv("M08_TEST_ADMIN_DATABASE_URL"), reason="Requires disposable PostgreSQL.")


def test_m09_upgrade_and_supported_rollback_preserve_frozen_history(database):
    url, engine = database
    migrate(url, "20261108_0010")
    sessions = sessionmaker(bind=engine)
    _import_content(sessions)
    uid, sid, eid, option = uuid4(), uuid4(), uuid4(), uuid4()
    with sessions.begin() as db:
        db.execute(User.__table__.insert().values(id=uid,email="rc-baseline@example.com",password_hash="synthetic-only"))
        db.execute(UserProfile.__table__.insert().values(user_id=uid,display_name="Synthetic M09 learner"))
        db.execute(UserPreferences.__table__.insert().values(user_id=uid))
        lesson = db.scalar(select(Lesson).where(Lesson.slug=="a1-001"))
        db.execute(LearningSession.__table__.insert().values(id=sid,user_id=uid,lesson_id=lesson.id,
            lesson_content_version=lesson.content_version,cefr_level="A1",status="completed",preview_mode=False,
            lesson_snapshot={"title":"Frozen M09 état", "sections":[{"title":"Original", "body_content":"Bonjour."}]},
            current_exercise_position=1,total_exercises=1,score_points=1,max_score_points=1,completed_at=utcnow()))
        db.execute(LearningSessionExercise.__table__.insert().values(id=eid,learning_session_id=sid,
            exercise_order=1,exercise_content_version=lesson.content_version,
            exercise_snapshot={"type":"multiple_choice","prompt":"Je ___ ici.","correct_option_id":str(option),"format_version":2},max_points=1))
        db.execute(ExerciseAttempt.__table__.insert().values(user_id=uid,learning_session_id=sid,session_exercise_id=eid,
            idempotency_key=uuid4(),submitted_answer=str(option),answer_payload={"selected_option_id":str(option)},
            normalized_answer=str(option),is_correct=True,awarded_points=1,max_points=1,
            feedback={"correct_answer":"suis","explanation":"Saved M09 feedback"},grading_version="deterministic-v2"))
    tables=("users","user_profiles","learning_sessions","learning_session_exercises","exercise_attempts")
    def fingerprints():
        with engine.connect() as db:
            return {name:db.execute(text(f"SELECT count(*)::text||':'||md5(string_agg(to_jsonb(t)::text,'' ORDER BY to_jsonb(t)::text)) FROM {name} t")).scalar_one() for name in tables}
    before=fingerprints()
    migrate(url,"head")
    assert fingerprints()==before
    with engine.connect() as db:
        assert db.execute(text("SELECT motivation_enabled FROM user_preferences WHERE user_id=:uid"),{"uid":uid}).scalar_one() is True
    migrate(url,"20261108_0010",downgrade=True)
    assert fingerprints()==before
    migrate(url,"head")
    assert fingerprints()==before
