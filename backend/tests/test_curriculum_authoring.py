from uuid import UUID, uuid4
import pytest

from sqlalchemy import select

from app.assessment_content import load_assessment_pack
from app.curriculum_models import Course, CurriculumRevision
from test_assessment_skills import skills
from test_interactive_learning import interactive
from test_learning import _csrf, _set_role

SLUG = "m10-assessments-a1-0.1.0"
BASE = f"/api/v1/content-review/{SLUG}"


def test_draft_edit_preserves_real_versions_invalidates_reviews_and_compares(skills):
    client, sessions, _ = skills
    detail = client.get(BASE).json()
    old = client.post(BASE + "/revisions", headers=_csrf(client)).json()
    assert client.post(BASE + "/revisions", headers=_csrf(client)).json()["id"] == old["id"]
    section = detail["content"]["lessons"][1]["sections"][0]
    body = dict(expected_digest=detail["digest"], next_version="0.1.1", section_id=section["id"],
                body_content=section["body_content"] + " Bonne lecture !")
    edited = client.post(BASE + "/sections", headers=_csrf(client), json=body)
    assert edited.status_code == 200, edited.text
    current = edited.json()
    assert current["version"] == "0.1.1" and current["id"] != old["id"]
    comparison = client.get(BASE + f"/compare?before={old['id']}&after={current['id']}")
    assert comparison.status_code == 200
    changed = next(item for item in comparison.json()["changes"] if item["path"].endswith("body_content"))
    assert changed["before"] == section["body_content"]
    assert changed["after"].endswith("Bonne lecture !")
    assert len(client.get(BASE + "/revisions").json()["items"]) == 2
    assert client.post(BASE + "/sections", headers=_csrf(client), json=body).status_code == 409
    detail = client.get(BASE).json()
    assert len(detail["readiness"]["outstanding"]) == 5
    assert not detail["readiness"]["complete"] and detail["technical_issues"] == []
    with sessions() as db:
        original = db.get(CurriculumRevision, UUID(old["id"]))
        assert original.packet["lessons"][1]["sections"][0]["body_content"] == section["body_content"]
        assert db.scalar(select(Course).where(Course.slug == SLUG)).status == "draft"


def test_authoring_denies_ordinary_users_cross_course_ids_and_published_edits(skills):
    client, sessions, _ = skills
    detail = client.get(BASE).json()
    section = detail["content"]["lessons"][0]["sections"][0]
    body = dict(expected_digest=detail["digest"], next_version="0.1.1", section_id=str(uuid4()), body_content="Draft body")
    assert client.post(BASE + "/sections", headers=_csrf(client), json=body).status_code == 404
    assert client.post(BASE + "/revisions").status_code == 403
    assert client.get(BASE + f"/compare?before={uuid4()}&after={uuid4()}").status_code == 404
    with sessions.begin() as db:
        db.scalar(select(Course).where(Course.slug == SLUG)).status = "published"
    detail = client.get(BASE).json()
    assert client.post(BASE + "/sections", headers=_csrf(client), json={**body,
        "section_id": section["id"], "expected_digest": detail["digest"]}).status_code == 409
    _set_role(sessions, "interactive@example.com", "learner")
    assert client.get(BASE + "/revisions").status_code == 403
    assert client.post(BASE + "/revisions", headers=_csrf(client)).status_code == 403
    assert client.get(BASE + f"/compare?before={uuid4()}&after={uuid4()}").status_code == 403


def test_create_single_draft_via_authoring_keeps_unpublished(skills):
    client, sessions, _ = skills
    body = load_assessment_pack().model_dump(mode="json")
    body["version"] = "0.2.0"
    original_license = client.get(BASE).json()["content"]["source_license"]
    body["source_license"] = "Separate original draft release; new independent rights review pending"
    body["tasks"] = [body["tasks"][2]]
    created = client.post("/api/v1/content-review/drafts", headers=_csrf(client), json=body)
    assert created.status_code == 200, created.text
    assert created.json()["report"]["lessons"] == 1
    assert client.get(BASE).json()["content"]["source_license"] == original_license
    assert client.post("/api/v1/content-review/drafts", headers=_csrf(client), json=body).json()["revision"]["id"] == created.json()["revision"]["id"]
    with sessions() as db:
        course = db.scalar(select(Course).where(Course.slug == created.json()["slug"]))
        assert course.status == "draft"


def test_lesson_details_are_versioned_and_failed_changes_are_atomic(skills):
    client, sessions, _ = skills
    detail = client.get(BASE).json()
    lesson = detail["content"]["lessons"][0]
    body = dict(expected_digest=detail["digest"], next_version="0.1.1", lesson_slug=lesson["slug"],
        title=lesson["title"], description=lesson["description"] + " Review the examples first.", estimated_minutes=14)
    assert client.post(BASE + "/lessons", headers=_csrf(client), json={**body, "title": " "}).status_code == 422
    assert client.get(BASE).json()["digest"] == detail["digest"]
    edited = client.post(BASE + "/lessons", headers=_csrf(client), json=body)
    assert edited.status_code == 200, edited.text
    versions = client.get(BASE + "/revisions").json()["items"]
    changes = client.get(BASE + f"/compare?before={versions[1]['id']}&after={versions[0]['id']}").json()["changes"]
    assert any(row["path"].endswith("description") and row["before"] == lesson["description"] for row in changes)
    assert client.get(BASE).json()["content"]["lessons"][0]["estimated_minutes"] == 14
    assert client.post(BASE + "/lessons", headers=_csrf(client), json=body).status_code == 409


def test_exercise_keys_preserve_snapshots_and_reject_invalid_or_foreign_choices(interactive):
    from app.curriculum_models import Lesson, Unit
    from app.learning_models import LearningSessionExercise
    from test_interactive_learning import start
    client, sessions, lesson_id = interactive
    saved = start(client, lesson_id)
    with sessions() as db:
        slug = db.scalar(select(Course.slug).join(Unit).join(Lesson).where(Lesson.id == UUID(str(lesson_id))))
        frozen = db.get(LearningSessionExercise, UUID(saved["exercises"][0]["id"])).exercise_snapshot.copy()
    base = f"/api/v1/content-review/{slug}"
    detail = client.get(base).json()
    exercise = detail["content"]["lessons"][0]["exercises"][0]
    options = [{**row, "is_correct": not row["is_correct"]} for row in exercise["options"]]
    # Pick exactly one different correct choice; preserve every stable option identifier.
    new_key = next(row["id"] for row in exercise["options"] if not row["is_correct"])
    for row in options:
        row["is_correct"] = row["id"] == new_key
    body = dict(expected_digest=detail["digest"], next_version="0.1.2", exercise_id=exercise["id"],
        prompt=exercise["prompt"], instructions=exercise["instructions"], explanation=exercise["feedback"], data=exercise["data"], options=options)
    assert client.post(base + "/exercises", json=body).status_code == 403
    bad = [{**row, "is_correct": True} for row in options]
    assert client.post(base + "/exercises", headers=_csrf(client), json={**body, "options": bad}).status_code == 422
    assert client.get(base).json()["digest"] == detail["digest"]
    assert client.get(base + "/revisions").json()["items"] == []
    assert client.post(base + "/exercises", headers=_csrf(client), json={**body,
        "options": [{**row, "id": str(uuid4())} for row in options]}).status_code == 422
    edited = client.post(base + "/exercises", headers=_csrf(client), json=body)
    assert edited.status_code == 200, edited.text
    with sessions() as db:
        assert db.get(LearningSessionExercise, UUID(saved["exercises"][0]["id"])).exercise_snapshot == frozen
    current = client.get(base).json()
    updated = current["content"]["lessons"][0]["exercises"][0]
    assert next(row["id"] for row in updated["options"] if row["is_correct"]) == new_key
    assert len(current["readiness"]["outstanding"]) == 5
    versions = client.get(base + "/revisions").json()["items"]
    old = versions[1]["id"]
    with sessions() as db:
        old_options = db.get(CurriculumRevision, UUID(old)).packet["lessons"][0]["exercises"][0]["options"]
        assert next(row["id"] for row in old_options if row["is_correct"]) == frozen["correct_option_id"]
    answer = client.post(f"/api/v1/learning/sessions/{saved['id']}/answers", headers=_csrf(client), json={
        "session_exercise_id": saved["exercises"][0]["id"], "selected_option_id": frozen["correct_option_id"],
        "idempotency_key": str(uuid4()),
    })
    assert answer.status_code == 200, answer.text
    assert answer.json()["is_correct"] is True
    _set_role(sessions, "interactive@example.com", "learner")
    assert client.post(base + "/exercises", headers=_csrf(client), json=body).status_code == 403


def test_course_provenance_and_ordered_prerequisites_preserve_versions(skills):
    client, sessions, _ = skills
    detail = client.get(BASE).json()
    content = detail["content"]
    body = {key: content[key] for key in ("title", "description", "estimated_minutes", "level", "source_license", "attribution", "source_url")}
    body.update(expected_digest=detail["digest"], next_version="0.1.1", source_license="Original staff draft, independent review pending")
    assert client.post(BASE + "/course", headers=_csrf(client), json={**body, "level": "B2"}).status_code == 422
    assert client.post(BASE + "/course", headers=_csrf(client), json=body).status_code == 200
    old = client.get(BASE + "/revisions").json()["items"][1]
    with sessions() as db:
        assert db.get(CurriculumRevision, UUID(old["id"])).packet["source_license"] == content["source_license"]
    detail = client.get(BASE).json()
    first, second = detail["content"]["lessons"][:2]
    body = dict(expected_digest=detail["digest"], next_version="0.1.2", lesson_slug=second["slug"],
        title=second["title"], description=second["description"], estimated_minutes=12, prerequisites=[first["id"]])
    assert client.post(BASE + "/lessons", headers=_csrf(client), json={**body, "prerequisites": [second["id"]]}).status_code == 422
    assert client.post(BASE + "/lessons", headers=_csrf(client), json=body).status_code == 200
    detail = client.get(BASE).json()
    assert detail["content"]["lessons"][1]["prerequisites"] == [first["id"]]
    assert client.post(BASE + "/lessons", headers=_csrf(client), json={**body, "expected_digest": detail["digest"],
        "next_version": "0.1.3", "lesson_slug": first["slug"], "prerequisites": [second["id"]]}).status_code == 422
    assert client.get(BASE).json()["digest"] == detail["digest"]


@pytest.mark.parametrize("kind,field", [
    ("objective", "description"), ("grammar_topic", "summary"), ("grammar_rule", "explanation_english"),
    ("grammar_example", "english_translation"), ("word_sense", "explanation_english"),
    ("translation", "translated_text"), ("example", "english_translation"), ("conjugation", "conjugated_form"),
])
def test_exclusive_resource_text_is_versioned_and_shared_edits_are_rejected(skills, kind, field):
    from app.curriculum_models import (ExampleSentence, GrammarTopic, GrammarRule, GrammarExample, LessonGrammar,
        Lexeme, WordSense, Translation, LexemeExample, LessonVocabulary, VerbLemma, VerbConjugation)
    client, sessions, _ = skills
    detail = client.get(BASE).json()
    lid = UUID(detail["content"]["lessons"][0]["id"])
    token = uuid4().hex[:8]
    with sessions.begin() as db:
        topic = GrammarTopic(slug="staff-"+token, title="Draft grammar", cefr_level="A1", summary="Original draft explanation", publication_status="draft")
        word = Lexeme(lemma="tester-"+token, normalized_lemma="tester-"+token, part_of_speech="verb")
        verb = VerbLemma(infinitive=word.lemma, normalized_infinitive=word.lemma, verb_group="first", irregular=False)
        db.add_all([topic, word, verb]); db.flush()
        rule = GrammarRule(topic_id=topic.id, rule_code="staff-rule", explanation_english="Use this original example.")
        sense = WordSense(lexeme_id=word.id, sense_number=1, definition_french="Un exemple original.", explanation_english="An original example.")
        example = ExampleSentence(french_text="Je teste.", english_translation="I test.", cefr_level="A1")
        db.add_all([rule, sense, example]); db.flush()
        db.add_all([LessonGrammar(lesson_id=lid, grammar_topic_id=topic.id),
            GrammarExample(rule_id=rule.id, french_sentence="Je teste.", english_translation="I test."),
            Translation(word_sense_id=sense.id, language_code="en", translated_text="to test"),
            LexemeExample(lexeme_id=word.id, example_sentence_id=example.id),
            LessonVocabulary(lesson_id=lid, lexeme_id=word.id, sequence_order=100),
            VerbConjugation(verb_id=verb.id, mood="indicative", tense="present", grammatical_person=1, grammatical_number="singular", conjugated_form="teste")])
    detail = client.get(BASE).json()
    resource = next(row for row in detail["content"]["resources"] if row["kind"] == kind and row["editable"])
    body = dict(expected_digest=detail["digest"], next_version="0.1.1", kind=kind,
        resource_id=resource["id"], values={field: "Reviewed draft text"})
    assert client.post(BASE + "/resources", headers=_csrf(client), json={**body, "values": {"id": str(uuid4())}}).status_code == 422
    edited = client.post(BASE + "/resources", headers=_csrf(client), json=body)
    assert edited.status_code == 200, edited.text
    history = client.get(BASE + "/revisions").json()["items"]
    changes = client.get(BASE + f"/compare?before={history[1]['id']}&after={history[0]['id']}").json()["changes"]
    assert any(row["after"] == "Reviewed draft text" for row in changes)
    detail = client.get(BASE).json()
    shared = next((row for row in detail["content"]["resources"] if not row["editable"] and row["kind"] == "word_sense"), None)
    assert shared is not None
    assert client.post(BASE + "/resources", headers=_csrf(client), json=dict(expected_digest=detail["digest"],
        next_version="0.1.2", kind="word_sense", resource_id=shared["id"], values={"explanation_english": "Must not change"})).status_code == 409
    assert client.get(BASE).json()["digest"] == detail["digest"]
