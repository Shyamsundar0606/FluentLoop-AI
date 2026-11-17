import os
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.assessment_content import import_assessment_pack, load_assessment_pack
from app.config import Settings
from app.curriculum_models import Course, Exercise, ExerciseOption, Lesson, LessonSection
from app.learning_models import LearningSessionExercise
from app.models import User, UserPreferences, utcnow
from app.services import assessment_service, curriculum_authoring, learning_service
from test_interactive_postgres import database, migrate
from test_learning import _import_content

pytestmark = pytest.mark.skipif(not os.getenv("M08_TEST_ADMIN_DATABASE_URL"),
                               reason="Requires disposable PostgreSQL authoring database.")


def test_postgres_versions_preserve_sessions_and_refuse_lossy_rollback(database, monkeypatch):
    url, engine = database
    migrate(url, "head")
    sessions = sessionmaker(bind=engine)
    _import_content(sessions)
    monkeypatch.setattr("app.services.draft_preview.get_settings", lambda: Settings(
        _env_file=None, APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=True))
    slug = "m10-assessments-a1-0.1.0"
    with sessions.begin() as db:
        import_assessment_pack(db, load_assessment_pack())
        user = User(email="version-author@example.com", role="admin", password_hash="unused-test-only",
                    email_verified_at=utcnow())
        db.add(user)
        db.flush()
        uid = user.id
        db.add(UserPreferences(user_id=uid))
    with sessions() as db:
        user = db.get(User, uid)
        lesson = db.scalar(select(Lesson).where(Lesson.slug.endswith("-message-from-lina")))
        saved = assessment_service.start(db, user, "reading", lesson.id)
        frozen = db.get(LearningSessionExercise, saved.exercises[0].id).exercise_snapshot.copy()
        old = curriculum_authoring.snapshot(db, user, slug)
        section = db.scalar(select(LessonSection).where(LessonSection.lesson_id == lesson.id))
        edited = curriculum_authoring.edit(db, user, slug, curriculum_authoring.EditSection(
            expected_digest=old["digest"], next_version="0.1.1", section_id=section.id,
            body_content=section.body_content + " Bonne lecture !"))
        comparison = curriculum_authoring.compare(db, slug, UUID(old["id"]), UUID(edited["id"]))
        assert any(item["path"].endswith("body_content") for item in comparison["changes"])
        assert db.get(LearningSessionExercise, saved.exercises[0].id).exercise_snapshot == frozen
        restored = learning_service.get_session(db, user=user, session_id=saved.id)
        assert restored.lesson_content_version == "0.1.0"
        assert "Bonne lecture" not in restored.lesson["assessment_context"]
        exercise = db.get(Exercise, saved.exercises[0].exercise_id)
        options = db.scalars(select(ExerciseOption).where(ExerciseOption.exercise_id == exercise.id)
                             .order_by(ExerciseOption.sequence_order)).all()
        new_key = next(option.id for option in options if not option.is_correct)
        curriculum_authoring.edit_exercise(db, user, slug, curriculum_authoring.EditExercise(
            expected_digest=edited["digest"], next_version="0.1.2", exercise_id=exercise.id,
            prompt=exercise.prompt, instructions=exercise.instructions, explanation=exercise.explanation,
            data=exercise.exercise_data, options=[dict(id=row.id, option_text=row.option_text,
                is_correct=row.id == new_key) for row in options]))
        assert db.get(LearningSessionExercise, saved.exercises[0].id).exercise_snapshot == frozen
        assert next(row.id for row in options if row.is_correct) == new_key
        assert db.scalar(select(Course).where(Course.slug == slug)).status == "draft"
    with engine.connect() as db:
        prior_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    migrate(url, "20261115_0011", success=False, downgrade=True)
    with engine.connect() as db:
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == prior_revision


def test_prerequisites_guard_lossy_rollback_in_postgres(database):
    from app.curriculum_models import LessonPrerequisite
    url, engine = database
    migrate(url, "head")
    sessions = sessionmaker(bind=engine)
    _import_content(sessions)
    with sessions.begin() as db:
        import_assessment_pack(db, load_assessment_pack())
        user = User(email="prerequisite-author@example.com", role="admin", password_hash="synthetic-only", email_verified_at=utcnow())
        db.add(user); db.flush(); uid = user.id
    with sessions() as db:
        course = db.scalar(select(Course).where(Course.slug == "m10-assessments-a1-0.1.0"))
        from app.curriculum_models import Unit
        lessons = db.scalars(select(Lesson).join(Unit).where(Unit.course_id == course.id).order_by(Lesson.sequence_order)).all()
        old = curriculum_authoring.snapshot(db, db.get(User, uid), course.slug)
        curriculum_authoring.edit_lesson(db, db.get(User, uid), course.slug, curriculum_authoring.EditLesson(
            expected_digest=old["digest"], next_version="0.1.1", lesson_slug=lessons[1].slug,
            title=lessons[1].title, description=lessons[1].description, estimated_minutes=12,
            prerequisites=[lessons[0].id]))
    with engine.connect() as db:
        prior_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    migrate(url, "20261115_0013", success=False, downgrade=True)
    with sessions() as db:
        assert len(db.scalars(select(LessonPrerequisite)).all()) == 1
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == prior_revision
