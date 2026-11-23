from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.assessment_content import import_assessment_pack, load_assessment_pack
from app.ai.providers.base import Generation, ProviderUnavailable
from app.curriculum_models import Lesson, LessonSection
from app.learning_models import LearningSessionExercise, WritingSubmission
from test_assessments import BASE, begin
from test_interactive_learning import interactive, answer_for
from test_learning import _csrf, _set_role
from test_learning import _register_and_login
from app.services.email import get_email_service


@pytest.fixture
def skills(interactive):
    client, sessions, _ = interactive
    with sessions.begin() as db:
        pack = load_assessment_pack()
        assert import_assessment_pack(db, pack)["reused"] is False
        assert import_assessment_pack(db, pack)["reused"] is True
        lessons = {skill: str(db.scalar(select(Lesson.id).where(
            Lesson.slug == f"m10-assessments-a1-0.1.0-{key}"))) for skill, key in (
                ("vocabulary", "polite-words"), ("reading", "message-from-lina"), ("writing", "introduce-yourself"))}
    return client, sessions, lessons


@pytest.mark.parametrize("skill", ["vocabulary", "reading"])
def test_objective_skill_grading_context_snapshots_and_results(skills, skill):
    client, sessions, lessons = skills
    catalog = client.get(BASE).json()
    assert {item["skill"] for item in catalog["items"]} == {"grammar", "listening", "reading", "vocabulary", "writing"}
    session = begin(client, lessons[skill], skill)
    if skill == "reading":
        assert "J'habite à Lyon" in session["lesson"]["assessment_context"]
        with sessions.begin() as db:
            passage = db.scalar(select(LessonSection).where(LessonSection.lesson_id == UUID(lessons[skill])))
            passage.body_content = "A later source edit must not replace an already saved reading passage."
        restored = client.get(f"/api/v1/learning/sessions/{session['id']}")
        assert "J'habite à Lyon" in restored.json()["lesson"]["assessment_context"]
    assert not any(key in str(session) for key in ("accepted_answers", "answer_pairs", "correct_option_id"))
    for exercise in session["exercises"]:
        with sessions() as db:
            frozen = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
        answer = answer_for(frozen)
        assert client.post(f"/api/v1/learning/sessions/{session['id']}/answers", headers=_csrf(client),
            json=dict(session_exercise_id=exercise["id"], idempotency_key=str(uuid4()), **answer)).json()["is_correct"]
    result = client.post(f"/api/v1/learning/sessions/{session['id']}/complete", headers=_csrf(client))
    assert result.status_code == 200 and result.json()["percentage"] == 100
    assert any(item["skill"] == skill for item in client.get(BASE + "/history").json()["items"])


def test_writing_persistence_idempotency_failure_retry_and_advisory_validation(skills, monkeypatch):
    client, sessions, lessons = skills
    body = dict(lesson_id=lessons["writing"], idempotency_key=str(uuid4()),
                text="Je m'appelle Lina. J'habite à Lyon. J'aime lire.")
    saved = client.post(BASE + "/writing", headers=_csrf(client), json=body)
    assert saved.status_code == 200, saved.text
    row = saved.json()
    assert row["original_text"] == body["text"] and row["feedback_status"] == "not_requested"
    assert "score" not in row and row["advisory_feedback"] is None
    assert client.post(BASE + "/writing", headers=_csrf(client), json=body).json()["id"] == row["id"]
    assert client.post(BASE + "/writing", headers=_csrf(client), json={**body, "text": "Different text"}).status_code == 409
    path = BASE + f"/writing/{row['id']}/feedback"

    class Offline:
        def generate(self, *args, **kwargs):
            raise ProviderUnavailable("private exception detail")
    monkeypatch.setattr("app.services.writing_service.get_provider", lambda: Offline())
    failed = client.post(path, headers=_csrf(client))
    assert failed.status_code == 200 and failed.json()["feedback_status"] == "unavailable"
    assert "private exception" not in failed.text and failed.json()["original_text"] == body["text"]

    class Invalid:
        def generate(self, *args, **kwargs):
            return Generation('{"score":100}', "test")
    monkeypatch.setattr("app.services.writing_service.get_provider", lambda: Invalid())
    assert client.post(path, headers=_csrf(client)).json()["feedback_status"] == "unavailable"

    class Advisory:
        def generate(self, messages, **kwargs):
            assert "email" not in messages[-1]["content"]
            return Generation('{"task_completion":"Three sentences address the task.","grammar_suggestions":[],"vocabulary_suggestions":["Try an additional activity word."],"clarity":"Your introduction is clear."}', "test")
    monkeypatch.setattr("app.services.writing_service.get_provider", lambda: Advisory())
    available = client.post(path, headers=_csrf(client)).json()
    assert available["feedback_status"] == "available" and available["original_text"] == body["text"]
    assert client.get(BASE + "/writing/history").json()["items"][0]["id"] == row["id"]
    assert client.get(BASE + "/insights").json()["writing"]["submissions"] == 1
    with sessions() as db:
        assert db.scalar(select(func.count(WritingSubmission.id))) == 1
    assert client.patch("/api/v1/users/me/preferences", headers=_csrf(client), json={"current_level": "a2"}).status_code == 200
    assert client.post(BASE + "/writing", headers=_csrf(client), json=body).json()["id"] == row["id"]
    _set_role(sessions, "interactive@example.com", "learner")
    assert client.get(BASE + f"/writing/{row['id']}").status_code == 404
    assert client.get(BASE + "/writing/history").json()["items"] == []
    assert client.get(BASE + f"/writing/tasks/{lessons['writing']}").status_code == 404


def test_release_edits_require_a_new_version(skills):
    _, sessions, _ = skills
    pack = load_assessment_pack()
    pack.tasks[0].title = "An edited draft title"
    with sessions.begin() as db, pytest.raises(ValueError, match="Increment"):
        import_assessment_pack(db, pack)


def test_authoring_schema_supports_exactly_six_levels():
    from pydantic import ValidationError
    from app.assessment_content import AssessmentPack

    body = load_assessment_pack().model_dump()
    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        assert AssessmentPack.model_validate({**body, "level": level}).level == level
    with pytest.raises(ValidationError):
        AssessmentPack.model_validate({**body, "level": "A0"})


def test_writing_auth_csrf_validation_and_cross_user_denial(skills):
    client, _, lessons = skills
    body = dict(lesson_id=lessons["writing"], idempotency_key=str(uuid4()), text="Bonjour !")
    assert client.post(BASE + "/writing", json=body).status_code == 403
    assert client.post(BASE + "/writing", headers=_csrf(client), json={**body, "text": "  "}).status_code == 422
    # Extended essays now allow 8000 characters; the over-limit rejection stays.
    assert client.post(BASE + "/writing", headers=_csrf(client), json={**body, "text": "x" * 8001}).status_code == 422
    saved = client.post(BASE + "/writing", headers=_csrf(client), json=body).json()
    client.cookies.clear()
    assert client.get(BASE + f"/writing/{saved['id']}").status_code == 401
    emails = client.app.dependency_overrides[get_email_service]()
    _register_and_login(client, emails, "writing-stranger@example.com")
    assert client.get(BASE + f"/writing/{saved['id']}").status_code == 404
    assert client.post(BASE + f"/writing/{saved['id']}/feedback", headers=_csrf(client)).status_code == 404
    assert client.get(BASE + "/writing/history").json()["items"] == []


def test_writing_migration_empty_rollback_and_saved_data_guard(skills):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect
    from app.models import User

    _, sessions, lessons = skills
    path = Path(__file__).resolve().parents[1] / "alembic/versions/20261115_0011_writing_submissions.py"
    spec = importlib.util.spec_from_file_location("writing_migration_test", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with sessions.begin() as db:
        connection = db.connection()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.op.drop_table("writing_submissions")
        migration.upgrade()
        assert {column["name"] for column in inspect(connection).get_columns("writing_submissions")} == set(WritingSubmission.__table__.columns.keys())
        migration.downgrade()
        assert not inspect(connection).has_table("writing_submissions")
        migration.upgrade()
        user = db.scalar(select(User).where(User.email == "interactive@example.com"))
        db.add(WritingSubmission(user_id=user.id, lesson_id=UUID(lessons["writing"]),
            idempotency_key=uuid4(), cefr_level="A1", lesson_content_version="0.1.0",
            prompt_snapshot="Original task", original_text="Bonjour !", preview_mode=True))
        db.flush()
        with pytest.raises(RuntimeError, match="discard saved writing"):
            migration.downgrade()
        assert db.scalar(select(func.count(WritingSubmission.id))) == 1


def test_skill_drafts_have_review_packets_and_no_manufactured_approvals(skills):
    from copy import deepcopy
    from app.course_review import validate_packet

    client, _, _ = skills
    slug = "m10-assessments-a1-0.1.0"
    detail = client.get(f"/api/v1/content-review/{slug}")
    assert detail.status_code == 200
    packet = detail.json()
    assert packet["technical_issues"] == []
    assert len(packet["readiness"]["outstanding"]) == 5
    assert packet["history"] == [] and not packet["readiness"]["complete"]
    for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
        content = deepcopy(packet["content"])
        content["level"] = level
        for lesson in content["lessons"]:
            lesson["level"] = level
            for exercise in lesson["exercises"]:
                exercise["level"] = level
        # This checks structural level support, not pedagogical suitability.
        assert validate_packet(content) == []
    content = deepcopy(packet["content"])
    content["lessons"][0]["exercises"][0]["objective"] = str(uuid4())
    assert any("invalid definition or key" in issue for issue in validate_packet(content))
