"""New manuscripts are exercised only in disposable fixture databases."""
import hashlib
import unicodedata
from collections import Counter
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from app.assessment_content import import_assessment_pack, load_assessment_pack, pack_digest
from app.curriculum_models import Course, Exercise, GrammarTopic, Lesson, Lexeme, Unit
from app.learning_models import LearningSessionExercise
from app.services.exercise_formats import snapshot, public_fields
from app.services.grading_service import grade_saved
from types import SimpleNamespace
from test_interactive_learning import interactive, answer_for, start
from test_learning import _csrf, _set_role

PACKS = sorted((Path(__file__).resolve().parents[1] / "content/personal").glob("*.json"))


def test_legacy_release_digest_is_unchanged():
    pack = load_assessment_pack()
    old = pack.model_dump(exclude={"title", "glossary", "learning_stage"})
    for task in old["tasks"]:
        for key in ("module_title", "estimated_minutes", "grammar", "prerequisites"):
            task.pop(key)
    import json
    expected = hashlib.sha256(json.dumps(old, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    assert pack_digest(pack) == expected


def test_release_coverage_and_format_counts():
    packs = [load_assessment_pack(path) for path in PACKS]
    assert {pack.level for pack in packs} == {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert sum(len(pack.tasks) for pack in packs) == 72
    assert sum(len(task.exercises) for pack in packs for task in pack.tasks) == 324
    for pack in packs:
        assert len(pack.glossary) == 9
        assert sum(len(task.grammar) for task in pack.tasks) == 3
        assert len({task.module_title for task in pack.tasks}) == 3
        for task in pack.tasks:
            assert task.skill == "writing" or {item.type for item in task.exercises} == {
                "multiple_choice", "fill_blank", "sentence_order", "matching", "listening", "short_answer"}


def test_every_authored_answer_key_roundtrips_without_public_key_leaks():
    checked = 0
    for path in PACKS:
        pack = load_assessment_pack(path)
        for task in pack.tasks:
            for number, item in enumerate(task.exercises, 1):
                exercise = SimpleNamespace(exercise_type=item.type, exercise_data=item.data,
                    prompt=item.prompt, instructions=item.instructions, explanation=item.explanation,
                    level=pack.level, sequence_order=number, learning_objective_id=None, grammar_topic_id=None)
                options = [SimpleNamespace(id=uuid4(), option_text=label, sequence_order=i + 1,
                           is_correct=i == item.correct_option) for i, label in enumerate(item.options)]
                saved = snapshot(exercise, options)
                assert grade_saved(saved, answer_for(saved))[0]
                answer = answer_for(saved)
                if item.type in ("multiple_choice", "listening"):
                    answer = {"selected_option_id": next(option["id"] for option in saved["options"]
                              if option["id"] != saved["correct_option_id"])}
                elif item.type in ("fill_blank", "short_answer"):
                    answer = {"text_answer": "A deliberately unrelated incorrect answer."}
                elif item.type == "sentence_order":
                    answer = {"tile_ids": list(reversed(saved["accepted_orders"][0]))}
                else:
                    keys, values = list(saved["answer_pairs"]), list(saved["answer_pairs"].values())
                    answer = {"matches": dict(zip(keys, values[1:] + values[:1]))}
                assert grade_saved(saved, answer)[0] is False
                assert not any(key in str(public_fields(saved)) for key in
                               ("accepted_answers", "answer_pairs", "correct_option_id"))
                checked += 1
    assert checked == 324


def test_reviewed_release_semantic_links_and_answer_position_balance():
    import importlib.util
    spec = importlib.util.spec_from_file_location("personal_builder", Path(__file__).resolve().parents[1] /
                                             "scripts/build_personal_curriculum.py")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    positions = Counter()
    for path in PACKS:
        pack = load_assessment_pack(path)
        assert pack.version == builder.VERSION == "0.2.1"
        assert pack.model_dump(mode="json") == type(pack).model_validate(builder.build(pack.level, builder.DATA[pack.level])).model_dump(mode="json")
        for task in pack.tasks:
            assert task.context == unicodedata.normalize("NFC", task.context)
            assert "Lesson focus:" in task.context
            if task.skill == "writing":
                assert "Include a request, an explanation and a suitable closing" not in task.context
                continue
            number = int(task.key.split("-")[1])
            row = builder.DATA[pack.level][number - 1]
            by_type = {item.type: item for item in task.exercises}
            listening = by_type["listening"]
            assert listening.data["text_fr"] == row[5]
            assert listening.options[listening.correct_option] == row[6]
            assert by_type["fill_blank"].data["accepted_answers"] == [row[8]]
            assert builder.GAP_INSTRUCTIONS[pack.level][number - 1] in by_type["fill_blank"].instructions
            assert by_type["short_answer"].data["accepted_answers"] == [row[5]]
            matching = by_type["matching"].data
            pairs = {left["id"]: left["text"] for left in matching["left_items"]}
            meanings = {right["id"]: right["text"] for right in matching["right_items"]}
            assert {(pairs[key], meanings[value]) for key, value in matching["answer_pairs"].items()} == {(fr,en) for fr,en,_ in row[9]}
            for item in task.exercises:
                if item.correct_option is not None:
                    positions[item.correct_option] += 1
    assert positions == {0: 36, 1: 36, 2: 36}


@pytest.mark.parametrize("path", PACKS, ids=lambda path: path.stem)
def test_new_release_import_grading_persistence_and_denial(interactive, path):
    client, sessions, _ = interactive
    pack = load_assessment_pack(path)
    with sessions.begin() as db:
        before = db.scalar(select(func.count(Lesson.id)))
        assert import_assessment_pack(db, pack)["reused"] is False
        assert import_assessment_pack(db, pack)["reused"] is True
        assert db.scalar(select(func.count(Lesson.id))) == before + 12
        course = db.scalar(select(Course).where(Course.slug == f"m10-assessments-{pack.level.lower()}-{pack.version}"))
        assert course.status == "draft"
        lessons = db.scalars(select(Lesson).join(Unit).where(Unit.course_id == course.id)).all()
        assert len(lessons) == 12 and all(lesson.status == "draft" for lesson in lessons)
        assert db.scalar(select(func.count(Exercise.id)).join(Lesson).join(Unit).where(Unit.course_id == course.id)) == 54
        topics = db.scalars(select(GrammarTopic).where(GrammarTopic.slug.like(course.slug + "-%"))).all()
        assert len(topics) == 3 and all(topic.publication_status == "draft" for topic in topics)
        lid = str(next(lesson.id for lesson in lessons if lesson.slug.endswith("module-1-grammar")))
    session = start(client, lid)
    assert len(session["exercises"]) == 6
    assert not any(key in str(session) for key in ("accepted_answers", "correct_option_id", "answer_pairs"))
    for exercise in session["exercises"]:
        with sessions() as db:
            saved = db.get(LearningSessionExercise, UUID(exercise["id"])).exercise_snapshot
        response = client.post(f"/api/v1/learning/sessions/{session['id']}/answers", headers=_csrf(client),
            json=dict(session_exercise_id=exercise["id"], idempotency_key=str(uuid4()), **answer_for(saved)))
        assert response.status_code == 200 and response.json()["is_correct"], response.text
        restored = client.get(f"/api/v1/learning/sessions/{session['id']}").json()
        assert next(item for item in restored["exercises"] if item["id"] == exercise["id"])["answered"]
    complete = client.post(f"/api/v1/learning/sessions/{session['id']}/complete", headers=_csrf(client))
    assert complete.status_code == 200 and complete.json()["percentage"] == 100
    _set_role(sessions, "interactive@example.com", "learner")
    assert client.get(f"/api/v1/learning/sessions/{session['id']}").status_code == 404
    assert client.post("/api/v1/learning/sessions", headers=_csrf(client), json={"lesson_id": lid}).status_code == 404


def test_shared_lexical_meaning_cannot_be_rewritten(interactive):
    _, sessions, _ = interactive
    pack = load_assessment_pack(PACKS[0])
    with sessions.begin() as db:
        entry = pack.glossary[0]
        db.add(Lexeme(lemma=entry.lemma, normalized_lemma=entry.lemma.casefold(), part_of_speech="phrase"))
    with sessions.begin() as db, pytest.raises(ValueError, match="cannot replace"):
        import_assessment_pack(db, pack)


def test_new_release_requires_new_version_after_edit(interactive):
    _, sessions, _ = interactive
    pack = load_assessment_pack(PACKS[0])
    with sessions.begin() as db:
        import_assessment_pack(db, pack)
    pack.tasks[0].context += " A changed manuscript."
    with sessions.begin() as db, pytest.raises(ValueError, match="Increment"):
        import_assessment_pack(db, pack)
