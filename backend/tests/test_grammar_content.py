from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.curriculum_models import ContentProvenance, Exercise, GrammarTopic, Lesson, Lexeme
from app.grammar_content import REVIEW_AREAS, Supplement, import_supplement, load_supplement
from app.interactive_content import import_pack, load_pack
from app.learning_models import LearningSessionExercise
from test_interactive_learning import answer_for, interactive, start
from test_learning import _csrf, _set_role


@pytest.mark.parametrize("failure", ["duplicate_topic", "wrong_audio_key", "wrong_order", "duplicate_word", "level"])
def test_rejects_invalid_grammar_source(failure):
    source = load_supplement().model_dump(mode="json")
    if failure == "duplicate_topic":
        source["topics"][1] = deepcopy(source["topics"][0])
    elif failure == "wrong_audio_key":
        source["topics"][0]["exercises"][1]["correct_option"] = 0
    elif failure == "wrong_order":
        source["topics"][5]["exercises"][1]["data"]["accepted_orders"][0].reverse()
    elif failure == "duplicate_word":
        source["topics"][0]["vocabulary"] *= 2
    else:
        source["level"] = "A2"
    with pytest.raises(ValidationError):
        Supplement.model_validate(source)


def test_import_preserves_source_ids_and_frozen_answers(interactive):
    client, sessions, fixture_id = interactive
    old_session = UUID(start(client, fixture_id)["id"])
    with sessions.begin() as db:
        snapshot_query = select(LearningSessionExercise.id, LearningSessionExercise.exercise_snapshot).where(
            LearningSessionExercise.learning_session_id == old_session)
        before = dict(db.execute(snapshot_query).all())
        legacy_ids = set(db.scalars(select(Exercise.id)))
        lexemes = db.scalar(select(func.count(Lexeme.id)))
        pack = load_supplement()
        report = import_supplement(db, pack)
        assert report["review"] == dict.fromkeys(REVIEW_AREAS, "pending")
        assert report["lessons"] == 12 and report["exercises"] == 25
        assert import_supplement(db, pack)["unchanged"]
        assert import_pack(db, load_pack())["updated"] == 0
        assert set(db.scalars(select(Exercise.id))) >= legacy_ids
        assert db.scalar(select(func.count(Lexeme.id))) == lexemes
        assert dict(db.execute(snapshot_query).all()) == before
        assert db.scalar(select(func.count(Lesson.id)).where(Lesson.status == "published")) == 0
        assert db.scalar(select(func.count(ContentProvenance.id)).where(
            ContentProvenance.review_state.in_(("human_reviewed", "published")))) == 0
        with pytest.raises(ValueError, match="immutable"):
            import_supplement(db, pack.model_copy(update={"attribution": "Changed existing release attribution"}))


def test_protected_topic_blocks_import_before_creating_lessons(interactive):
    _, sessions, _ = interactive
    with sessions.begin() as db:
        topic = db.scalar(select(GrammarTopic).where(GrammarTopic.slug == "polite-register"))
        topic.publication_status = "published"
        before = db.scalar(select(func.count(Lesson.id)))
        with pytest.raises(ValueError, match="protected grammar topic"):
            import_supplement(db, load_supplement())
        assert db.scalar(select(func.count(Lesson.id))) == before


def test_draft_grammar_session_uses_linked_content_and_evidence(interactive):
    client, sessions, _ = interactive
    with sessions.begin() as db:
        import_supplement(db, load_supplement())
        topic = str(db.scalar(select(GrammarTopic.id).where(GrammarTopic.slug == "introducing-yourself")))
    grammar = client.get("/api/v1/learning/grammar?level=A1").json()["items"]
    entry = next(item for item in grammar if item["id"] == topic)
    assert len(grammar) == 13 and entry["available_exercises"] == 3
    assert len(entry["rules"][0]["examples"]) == 3
    assert len(entry["objectives"]) == 1 and len(entry["vocabulary"]) == 3
    path = "/api/v1/learning/practice/sessions"
    request = {"category": "grammar", "level": "A1", "grammar_topic_id": topic}
    response = client.post(path, json=request, headers=_csrf(client))
    assert response.status_code == 200, response.text
    session = response.json()
    assert [item["type"] for item in session["exercises"]] == ["multiple_choice", "listening", "short_answer"]
    assert "text_fr" not in response.text and "accepted_answers" not in response.text
    for exercise in session["exercises"]:
        with sessions() as db:
            saved = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
        answer = answer_for(saved)
        if exercise["type"] == "short_answer":
            answer = {"text_answer": "Je suis Marie."}
        result = client.post(f"/api/v1/learning/sessions/{session['id']}/answers", headers=_csrf(client), json={
            "session_exercise_id": exercise["id"], "idempotency_key": str(uuid4()), **answer})
        assert result.status_code == 200
        assert result.json()["is_correct"] == (exercise["type"] != "short_answer")
    recommendations = client.get("/api/v1/study/recommendations").json()
    assert any(item.get("practice_category") == "mistakes" and item["evidence_attempt_ids"] for item in recommendations)
    _set_role(sessions, "interactive@example.com", "learner")
    assert client.get("/api/v1/learning/grammar?level=A1").json()["items"] == []
    assert client.get(f"/api/v1/lessons/{session['lesson_id']}").status_code == 404
    assert client.post(path, json=request, headers=_csrf(client)).status_code == 409
