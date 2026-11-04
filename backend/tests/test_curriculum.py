from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.content_import import _import_data, _lemma_for_storage, _norm, load_content
from app.content_report import build_report
from app.content_schemas import A1PublicationReviewRecord
from app.publish_content import publish_course
from app.curriculum_models import (
    ContentSource,
    CefrLevel,
    ContentProvenance,
    Course,
    Dialogue,
    DialogueTurn,
    Exercise,
    ExerciseAnswer,
    ExerciseOption,
    ExampleSentence,
    GrammarExample,
    GrammarRule,
    GrammarTopic,
    ImportBatch,
    Lesson,
    LessonDialogue,
    LessonGrammar,
    LessonVocabulary,
    Lexeme,
    Phoneme,
    Pronunciation,
    Translation,
    Unit,
    VerbConjugation,
    VerbLemma,
    WordSense,
)

CONTENT_PATH = Path(__file__).resolve().parents[1] / "content" / "a1" / "course.json"
REVIEW_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "content"
    / "reviews"
    / "A1_PUBLICATION_REVIEW_TEMPLATE.json"
)
PASSWORD = "StrongPassphrase2026"


def _login(client, emails, sessions, email: str = "curriculum@example.com") -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "display_name": "Curriculum learner",
        },
    )
    assert response.status_code == 201
    match = re.search(r"/verify-email#token=([A-Za-z0-9_-]+)", emails.messages[-1]["body"])
    assert match
    assert client.post("/api/v1/auth/verify-email", json={"token": match.group(1)}).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


def _import(sessions) -> dict[str, int]:
    content = load_content(CONTENT_PATH)
    with sessions.begin() as db:
        if db.scalar(select(func.count(CefrLevel.id))) == 0:
            db.add_all(
                [
                    CefrLevel(
                        code=code,
                        display_name=code,
                        description=f"{code} French",
                        rank=rank,
                    )
                    for rank, code in enumerate(("A1", "A2", "B1", "B2", "C1", "C2"), start=1)
                ]
            )
            db.flush()
        return _import_data(db, content)


def _publish_a1(sessions) -> None:
    record = _approved_test_review_record()
    with sessions.begin() as db:
        result = publish_course(db, record)
        assert result["lessons_published"] == 10
        outline = db.scalar(
            select(ContentProvenance).where(
                ContentProvenance.item_type == "course",
                ContentProvenance.item_key == "a2-everyday-independence",
            )
        )
        assert outline is not None
        assert outline.review_state == "automated_checked"


def _approval(reviewer: str) -> dict[str, object]:
    return {
        "status": "approved",
        "reviewer": reviewer,
        "independent_from_content_generation": True,
        "evidence_reference": "isolated automated test fixture only",
        "reviewed_at": datetime(2026, 11, 1, tzinfo=timezone.utc).isoformat(),
    }


def _approved_test_review_record() -> A1PublicationReviewRecord:
    content = load_content(CONTENT_PATH)
    return A1PublicationReviewRecord.model_validate(
        {
            "schema_version": 1,
            "course_slug": content.course.slug,
            "content_version": content.version,
            "source_sha256": hashlib.sha256(content.model_dump_json().encode("utf-8")).hexdigest(),
            "license_and_attribution": _approval("test rights reviewer"),
            "lessons": [
                {
                    "lesson_slug": lesson.slug,
                    "french_language": _approval("test French reviewer"),
                    "pedagogy_and_sequence": _approval("test pedagogy reviewer"),
                    "exercise_answers": _approval("test answer reviewer"),
                }
                for lesson in content.course.lessons
            ],
        }
    )


def test_curriculum_source_validates_six_levels_and_ai_assisted_a1_content():
    content = load_content(CONTENT_PATH)
    assert [course.level for course in content.planned_courses] == ["A2", "B1", "B2", "C1", "C2"]
    assert len(content.course.lessons) == 10
    assert sum(len(lesson.vocabulary) for lesson in content.course.lessons) == 83
    assert all(len(lesson.exercises) >= 5 for lesson in content.course.lessons)
    assert sum(len(lesson.exercises) for lesson in content.course.lessons) == 50
    assert any("sœur" in word.lemma for lesson in content.course.lessons for word in lesson.vocabulary)
    assert content.source_type == "ai_assisted_draft"
    assert "no publication license asserted" in content.source_license
    assert all(
        {exercise.correct_option for exercise in lesson.exercises} == {0, 1, 2}
        for lesson in content.course.lessons
    )
    assert [
        sum(exercise.correct_option == position for lesson in content.course.lessons for exercise in lesson.exercises)
        for position in range(3)
    ] == [17, 17, 16]
    lexical_entries: dict[tuple[str, str, str | None], list[tuple[str, str]]] = defaultdict(list)
    prompts = []
    for lesson in content.course.lessons:
        for word in lesson.vocabulary:
            identity = (
                unicodedata.normalize("NFKC", _lemma_for_storage(word.lemma, word.part_of_speech)).casefold(),
                word.part_of_speech,
                word.grammatical_gender,
            )
            lexical_entries[identity].append((word.translation, word.definition_french))
        prompts.extend(exercise.prompt for exercise in lesson.exercises)
    assert len(lexical_entries) == 78
    assert sum(len(entries) - 1 for entries in lexical_entries.values()) == 5
    assert all(len(set(entries)) == 1 for entries in lexical_entries.values())
    assert len(prompts) == len(set(prompts)) == 50


def test_unapproved_publication_template_is_rejected():
    with pytest.raises(ValueError):
        A1PublicationReviewRecord.model_validate_json(
            REVIEW_TEMPLATE_PATH.read_text(encoding="utf-8")
        )


def test_content_import_is_repeatable_and_keeps_drafts_unpublished(api_client):
    _client, sessions, _emails = api_client
    _import(sessions)
    rerun = _import(sessions)
    assert rerun["inserted"] == 0
    assert rerun["unchanged"] > 0
    with sessions() as db:
        assert db.scalar(select(func.count(Course.id))) == 6
        assert db.scalar(select(func.count(Unit.id))) == 20
        assert db.scalar(select(func.count(Lesson.id))) == 10
        assert db.scalar(select(func.count(Exercise.id))) == 50
        assert db.scalar(select(func.count(Lexeme.id))) < 80
        assert db.scalar(select(func.count(Lesson.id)).where(Lesson.status == "published")) == 0
        assert db.scalar(select(func.count(ContentProvenance.id))) > 100


def test_content_report_lists_import_counts_and_draft_status(api_client):
    _client, sessions, _emails = api_client
    _import(sessions)

    with sessions() as db:
        report = build_report(db)

    assert report["courses"] == 6
    assert report["lessons"] == 10
    assert report["draft_lessons"] == 10
    assert report["published_lessons"] == 0
    assert len(report["import_batches"]) == 1
    assert report["import_batches"][0]["status"] == "completed"


def test_content_import_removes_stale_grammar_examples_on_version_update(api_client):
    _client, sessions, _emails = api_client
    content = load_content(CONTENT_PATH)
    _import(sessions)

    with sessions.begin() as db:
        topic = db.scalar(select(GrammarTopic).where(GrammarTopic.slug == "simple-questions"))
        assert topic is not None
        rule = db.scalar(
            select(GrammarRule).where(
                GrammarRule.topic_id == topic.id,
                GrammarRule.rule_code == "basic-question-forms",
            )
        )
        assert rule is not None
        db.add(
            GrammarExample(
                rule_id=rule.id,
                french_sentence="Tu as un téléphone ?",
                english_translation="Do you have a phone? (informal)",
            )
        )

    next_version = "1.0.2"
    changed = content.model_copy(
        update={
            "version": next_version,
            "course": content.course.model_copy(update={"version": next_version}),
        }
    )
    with sessions.begin() as db:
        result = _import_data(db, changed)
    assert result["deleted"] == 1

    expected_examples = {
        tuple(example)
        for lesson in content.course.lessons
        for grammar in lesson.grammar
        if grammar.slug == "simple-questions" and grammar.rule_code == "basic-question-forms"
        for example in grammar.examples
    }
    with sessions() as db:
        topic = db.scalar(select(GrammarTopic).where(GrammarTopic.slug == "simple-questions"))
        rule = db.scalar(
            select(GrammarRule).where(
                GrammarRule.topic_id == topic.id,
                GrammarRule.rule_code == "basic-question-forms",
            )
        )
        actual_examples = db.scalars(
            select(GrammarExample).where(GrammarExample.rule_id == rule.id)
        ).all()
    assert {
        (example.french_sentence, example.english_translation) for example in actual_examples
    } == expected_examples


def test_imported_content_cross_references_and_answer_keys(api_client):
    _client, sessions, _emails = api_client
    content = load_content(CONTENT_PATH)
    _import(sessions)

    with sessions() as db:
        course = db.scalar(select(Course).where(Course.slug == content.course.slug))
        assert course is not None
        assert course.status == "draft"
        lessons = db.scalars(
            select(Lesson).join(Unit).where(Unit.course_id == course.id).order_by(Lesson.slug)
        ).all()
        assert [lesson.slug for lesson in lessons] == [f"a1-{index:03d}" for index in range(1, 11)]

        source = db.scalar(select(ContentSource).where(ContentSource.source_name == content.source_name))
        batch = db.scalar(select(ImportBatch).where(ImportBatch.batch_key == f"a1-starter-{content.version}"))
        assert source is not None and source.source_type == "ai_assisted_draft"
        assert source.source_license == content.source_license
        assert batch is not None and batch.status == "completed"
        provenance = db.scalars(
            select(ContentProvenance).where(ContentProvenance.import_batch_id == batch.id)
        ).all()
        assert provenance
        assert all(item.validation_status == "passed" for item in provenance)
        assert all(item.review_state == "automated_checked" for item in provenance)
        assert all(item.review_metadata == {"independent_human_review": False} for item in provenance)

        for source_lesson, lesson in zip(content.course.lessons, lessons):
            linked_words = db.scalars(
                select(Lexeme)
                .join(LessonVocabulary, LessonVocabulary.lexeme_id == Lexeme.id)
                .where(LessonVocabulary.lesson_id == lesson.id)
            ).all()
            assert len(linked_words) == len(source_lesson.vocabulary)
            for source_word in source_lesson.vocabulary:
                lemma = _lemma_for_storage(source_word.lemma, source_word.part_of_speech)
                word = db.scalar(
                    select(Lexeme).where(
                        Lexeme.normalized_lemma == _norm(lemma),
                        Lexeme.part_of_speech == source_word.part_of_speech,
                        Lexeme.grammatical_gender == source_word.grammatical_gender,
                    )
                )
                assert word is not None
                assert db.scalar(
                    select(LessonVocabulary).where(
                        LessonVocabulary.lesson_id == lesson.id,
                        LessonVocabulary.lexeme_id == word.id,
                    )
                ) is not None
                sense = db.scalar(select(WordSense).where(WordSense.lexeme_id == word.id))
                assert sense is not None
                assert sense.definition_french == source_word.definition_french
                assert db.scalar(
                    select(Translation.translated_text).where(
                        Translation.word_sense_id == sense.id,
                        Translation.language_code == "en",
                    )
                ) == source_word.translation
                if source_word.ipa:
                    assert db.scalar(
                        select(Pronunciation).where(
                            Pronunciation.lexeme_id == word.id,
                            Pronunciation.ipa == source_word.ipa,
                        )
                    ) is not None

            for source_example in source_lesson.examples:
                assert db.scalar(
                    select(ExampleSentence).where(
                        ExampleSentence.french_text == source_example.french_text,
                        ExampleSentence.english_translation == source_example.english_translation,
                    )
                ) is not None

            for source_grammar in source_lesson.grammar:
                topic = db.scalar(select(GrammarTopic).where(GrammarTopic.slug == source_grammar.slug))
                assert topic is not None
                assert db.scalar(
                    select(LessonGrammar).where(
                        LessonGrammar.lesson_id == lesson.id,
                        LessonGrammar.grammar_topic_id == topic.id,
                    )
                ) is not None
                rule = db.scalar(
                    select(GrammarRule).where(
                        GrammarRule.topic_id == topic.id,
                        GrammarRule.rule_code == source_grammar.rule_code,
                    )
                )
                assert rule is not None and rule.explanation_english == source_grammar.explanation_english
                actual_grammar_examples = db.scalars(
                    select(GrammarExample).where(GrammarExample.rule_id == rule.id)
                ).all()
                assert len(actual_grammar_examples) == len(source_grammar.examples)
                assert {
                    (item.french_sentence, item.english_translation) for item in actual_grammar_examples
                } == {tuple(item) for item in source_grammar.examples}

            dialogue = db.scalar(select(Dialogue).where(Dialogue.slug == source_lesson.dialogue.slug))
            assert dialogue is not None
            assert db.scalar(
                select(LessonDialogue).where(
                    LessonDialogue.lesson_id == lesson.id,
                    LessonDialogue.dialogue_id == dialogue.id,
                )
            ) is not None
            turns = db.scalars(
                select(DialogueTurn)
                .where(DialogueTurn.dialogue_id == dialogue.id)
                .order_by(DialogueTurn.sequence_order)
            ).all()
            assert [
                (turn.french_text, turn.english_translation)
                for turn in turns
            ] == [
                (turn.french_text, turn.english_translation)
                for turn in source_lesson.dialogue.turns
            ]

            for order, source_exercise in enumerate(source_lesson.exercises, start=1):
                exercise = db.scalar(
                    select(Exercise).where(
                        Exercise.lesson_id == lesson.id,
                        Exercise.sequence_order == order,
                    )
                )
                assert exercise is not None
                options = db.scalars(
                    select(ExerciseOption)
                    .where(ExerciseOption.exercise_id == exercise.id)
                    .order_by(ExerciseOption.sequence_order)
                ).all()
                assert [option.option_text for option in options] == source_exercise.options
                assert [
                    index for index, option in enumerate(options) if option.is_correct
                ] == [source_exercise.correct_option]
                answer = db.scalar(
                    select(ExerciseAnswer).where(ExerciseAnswer.exercise_id == exercise.id)
                )
                assert answer is not None
                assert answer.accepted_answer == source_exercise.options[source_exercise.correct_option]

        conjugations = db.scalars(
            select(VerbConjugation).join(VerbLemma).where(
                VerbConjugation.mood == "indicative",
                VerbConjugation.tense == "present",
            )
        ).all()
        assert len(conjugations) == 42
        expected_paradigms = {
            "être": ("suis", "es", "est", "sommes", "êtes", "sont"),
            "avoir": ("ai", "as", "a", "avons", "avez", "ont"),
            "aller": ("vais", "vas", "va", "allons", "allez", "vont"),
            "faire": ("fais", "fais", "fait", "faisons", "faites", "font"),
            "parler": ("parle", "parles", "parle", "parlons", "parlez", "parlent"),
            "habiter": ("habite", "habites", "habite", "habitons", "habitez", "habitent"),
            "aimer": ("aime", "aimes", "aime", "aimons", "aimez", "aiment"),
        }
        for infinitive, expected_forms in expected_paradigms.items():
            verb = db.scalar(select(VerbLemma).where(VerbLemma.infinitive == infinitive))
            assert verb is not None
            actual_forms = db.scalars(
                select(VerbConjugation)
                .where(VerbConjugation.verb_id == verb.id)
            ).all()
            by_person = {
                (form.grammatical_person, form.grammatical_number): form.conjugated_form
                for form in actual_forms
            }
            assert tuple(
                by_person[key]
                for key in (
                    (1, "singular"), (2, "singular"), (3, "singular"),
                    (1, "plural"), (2, "plural"), (3, "plural"),
                )
            ) == expected_forms
        assert db.scalar(select(func.count(Phoneme.id))) == 6


def test_publication_requires_complete_human_review_and_separate_license_approval(api_client):
    _client, sessions, _emails = api_client
    _import(sessions)
    incomplete = _approved_test_review_record().model_dump(mode="json")
    incomplete["lessons"].pop()

    with sessions.begin() as db:
        with pytest.raises(ValueError):
            publish_course(db, incomplete)
        stale_digest = _approved_test_review_record().model_dump(mode="json")
        stale_digest["source_sha256"] = "0" * 64
        with pytest.raises(ValueError, match="source digest"):
            publish_course(db, stale_digest)
        invalid_independence = _approved_test_review_record().model_dump(mode="json")
        invalid_independence["license_and_attribution"]["reviewer"] = "test French reviewer"
        with pytest.raises(ValueError, match="separate human reviewer"):
            publish_course(db, invalid_independence)

    with sessions() as db:
        course = db.scalar(select(Course).where(Course.slug == "a1-french-from-the-beginning"))
        assert course is not None and course.status == "draft"
        assert db.scalar(select(func.count(Lesson.id)).where(Lesson.status == "published")) == 0


def test_source_changes_require_version_increment_and_reopen_content_for_review(api_client):
    _client, sessions, _emails = api_client
    _import(sessions)
    original = load_content(CONTENT_PATH)
    changed_course = original.course.model_copy(
        update={"description": original.course.description + " Updated draft."}
    )
    with sessions.begin() as db:
        with pytest.raises(ValueError, match="without a version increment"):
            _import_data(db, original.model_copy(update={"course": changed_course}))

    next_version = "1.0.2"
    changed = original.model_copy(
        update={
            "version": next_version,
            "course": changed_course.model_copy(update={"version": next_version}),
        }
    )
    with sessions.begin() as db:
        result = _import_data(db, changed)
        assert result["updated"] > 0
    with sessions() as db:
        course = db.scalar(select(Course).where(Course.slug == "a1-french-from-the-beginning"))
        assert course is not None
        assert course.status == "draft"
        assert course.content_version == next_version


def test_curriculum_apis_hide_drafts_and_never_expose_answer_keys(api_client):
    client, sessions, emails = api_client
    _login(client, emails, sessions)
    _import(sessions)

    levels = client.get("/api/v1/levels")
    assert levels.status_code == 200
    assert [level["code"] for level in levels.json()] == ["A1", "A2", "B1", "B2", "C1", "C2"]
    assert all(level["content_available"] is False for level in levels.json())
    assert client.get("/api/v1/courses?level=A1").json()["items"] == []
    assert client.get("/api/v1/courses?level=A0").status_code == 422

    with sessions() as db:
        draft = db.scalar(select(Course).where(Course.slug == "a1-french-from-the-beginning"))
        lesson = db.scalar(select(Lesson).where(Lesson.slug == "a1-001"))
        assert draft and lesson
        draft_id = str(draft.id)
        lesson_id = str(lesson.id)
    assert client.get(f"/api/v1/courses/{draft_id}").status_code == 404
    assert client.get(f"/api/v1/lessons/{lesson_id}").status_code == 404
    assert client.get("/api/v1/vocabulary?level=A1&search=bonjour").json()["items"] == []

    _publish_a1(sessions)
    _import(sessions)
    courses = client.get("/api/v1/courses?level=A1")
    assert courses.status_code == 200
    assert courses.json()["total"] == 1
    course_id = courses.json()["items"][0]["id"]
    units = client.get(f"/api/v1/courses/{course_id}/units").json()
    assert units["total"] == 5
    lesson_rows = client.get(f"/api/v1/units/{units['items'][0]['id']}/lessons").json()
    assert lesson_rows["total"] == 2
    lesson_id = lesson_rows["items"][0]["id"]

    detail = client.get(f"/api/v1/lessons/{lesson_id}")
    assert detail.status_code == 200
    assert detail.json()["sections"]
    vocabulary = client.get(f"/api/v1/lessons/{lesson_id}/vocabulary")
    assert vocabulary.status_code == 200
    assert vocabulary.json()["total"] == 8
    grammar = client.get(f"/api/v1/lessons/{lesson_id}/grammar")
    assert grammar.json()["total"] == 1
    exercises = client.get(f"/api/v1/lessons/{lesson_id}/exercises")
    assert exercises.status_code == 200
    assert exercises.json()["total"] == 5
    assert "is_correct" not in exercises.text
    assert "correct_option" not in exercises.text
    assert "accepted_answer" not in exercises.text

    dialogues = client.get("/api/v1/dialogues?level=A1")
    assert dialogues.status_code == 200
    assert dialogues.json()["total"] >= 1
    assert client.get("/api/v1/vocabulary?level=A1&search=bonjour").json()["total"] >= 1
    assert client.get("/api/v1/grammar?level=A1").json()["total"] >= 1
    assert client.get("/api/v1/verbs/être/conjugations").status_code == 200

    empty_level = client.get("/api/v1/courses?level=C1")
    assert empty_level.status_code == 200
    assert empty_level.json()["items"] == []
    assert client.get("/api/v1/users/me/preferences").json()["current_level"] == "a1"
    assert client.get("/api/v1/lessons/not-a-uuid").status_code == 422


def test_curriculum_api_requires_authentication_and_limits_pagination(api_client):
    client, sessions, emails = api_client
    assert client.get("/api/v1/levels").status_code == 401
    _login(client, emails, sessions)
    response = client.get("/api/v1/courses?level=A1&limit=101")
    assert response.status_code == 422
