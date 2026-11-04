from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content_schemas import ContentImportInput, LessonInput
from app.core.database import SessionLocal
from app.curriculum_models import (
    CefrLevel,
    ContentProvenance,
    ContentSource,
    Course,
    Dialogue,
    DialogueTurn,
    ExampleSentence,
    Exercise,
    ExerciseAnswer,
    ExerciseOption,
    GrammarExample,
    GrammarRule,
    GrammarTopic,
    ImportBatch,
    Lesson,
    LessonDialogue,
    LessonGrammar,
    LessonObjective,
    LessonSection,
    LessonVocabulary,
    LearningObjective,
    Lexeme,
    LexemeExample,
    Phoneme,
    Pronunciation,
    Translation,
    Unit,
    VerbConjugation,
    VerbLemma,
    WordSense,
)


CONTENT_PATH = Path(__file__).resolve().parents[1] / "content" / "a1" / "course.json"
COUNTER = Counter()


class ContentSourceError(ValueError):
    pass


def _norm(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _lemma_for_storage(lemma: str, part_of_speech: str) -> str:
    value = lemma.strip()
    if part_of_speech == "noun":
        value = re.sub(r"^(?:un|une|le|la|l')\s*", "", value, flags=re.IGNORECASE)
    return value


def _upsert(
    db: Session,
    model: type,
    lookup: dict[str, Any],
    values: dict[str, Any],
    *,
    reopen_for_review: bool = False,
) -> Any:
    row = db.scalar(select(model).filter_by(**lookup))
    if row is None:
        row = model(**lookup, **values)
        db.add(row)
        db.flush()
        COUNTER["inserted"] += 1
        return row
    changed = False
    content_values = {key: value for key, value in values.items() if not (reopen_for_review and key == "status")}
    for key, value in content_values.items():
        if getattr(row, key) != value:
            setattr(row, key, value)
            changed = True
    if changed and reopen_for_review and row.status != "draft":
        row.status = "draft"
    COUNTER["updated" if changed else "unchanged"] += 1
    if changed:
        db.flush()
    return row


def _provenance(
    db: Session,
    source: ContentSource,
    batch: ImportBatch,
    item_type: str,
    item_key: str,
    version: str,
) -> None:
    lookup = {"item_type": item_type, "item_key": item_key, "content_version": version}
    existing = db.scalar(select(ContentProvenance).filter_by(**lookup))
    review_state = "automated_checked"
    review_metadata = {"independent_human_review": False}
    if existing is not None and existing.review_state in {"human_reviewed", "published"}:
        review_state = existing.review_state
        review_metadata = existing.review_metadata
    _upsert(
        db,
        ContentProvenance,
        lookup,
        {
            "source_id": source.id,
            "import_batch_id": batch.id,
            "validation_status": "passed",
            "review_state": review_state,
            "review_metadata": review_metadata,
        },
    )


def _objective(db: Session, item: dict[str, str], level: str) -> LearningObjective:
    return _upsert(
        db,
        LearningObjective,
        {"code": item["code"]},
        {
            "level": level,
            "title": item["title"],
            "description": item["description"],
            "skill_category": item["skill_category"],
        },
    )


def _section(db: Session, lesson: Lesson, section_type: str, title: str, body: str, order: int) -> None:
    _upsert(
        db,
        LessonSection,
        {"lesson_id": lesson.id, "sequence_order": order},
        {"section_type": section_type, "title": title, "body_content": body, "content_metadata": {}},
    )


def _import_lesson(
    db: Session,
    source: ContentSource,
    batch: ImportBatch,
    data: LessonInput,
    unit: Unit,
    position: int,
    version: str,
    grammar_examples_by_rule: dict[tuple[str, str], set[tuple[str, str]]],
) -> None:
    lesson = _upsert(
        db,
        Lesson,
        {"unit_id": unit.id, "slug": data.slug},
        {
            "title": data.title,
            "description": data.introduction,
            "sequence_order": position,
            "estimated_minutes": data.estimated_minutes,
            "difficulty_level": "A1",
            "explanation_language": "en",
            "status": "draft",
            "content_version": version,
        },
        reopen_for_review=True,
    )
    _provenance(db, source, batch, "lesson", data.slug, version)

    section_data = (
        ("introduction", "Introduction", data.introduction),
        ("pronunciation", "Pronunciation", data.pronunciation),
        ("practice", "Practice", "Short exercises check the key words and forms introduced in this lesson."),
        ("recap", "Recap", data.recap),
    )
    for order, (kind, title, body) in enumerate(section_data, start=1):
        _section(db, lesson, kind, title, body, order)
        _provenance(db, source, batch, "lesson_section", f"{data.slug}:{order}", version)

    for objective_data in data.objectives:
        objective = _objective(db, objective_data.model_dump(), "A1")
        _upsert(
            db,
            LessonObjective,
            {"lesson_id": lesson.id, "objective_id": objective.id},
            {},
        )
        _provenance(db, source, batch, "learning_objective", objective.code, version)

    lexemes: list[Lexeme] = []
    for order, word in enumerate(data.vocabulary, start=1):
        lemma = _lemma_for_storage(word.lemma, word.part_of_speech)
        normalized = _norm(lemma)
        identity = {
            "normalized_lemma": normalized,
            "part_of_speech": word.part_of_speech,
            "grammatical_gender": word.grammatical_gender,
        }
        lexeme = _upsert(
            db,
            Lexeme,
            identity,
            {"lemma": lemma, "irregularity_notes": word.irregularity_notes},
        )
        lexemes.append(lexeme)
        sense = _upsert(
            db,
            WordSense,
            {"lexeme_id": lexeme.id, "sense_number": 1},
            {
                "definition_french": word.definition_french,
                "explanation_english": word.translation,
                "usage_notes": word.teaching_note,
            },
        )
        lexical_key = f"{normalized}:{word.part_of_speech}:{word.grammatical_gender or ''}"
        _provenance(db, source, batch, "word_sense", f"{lexical_key}:1", version)
        translation = _upsert(
            db,
            Translation,
            {"word_sense_id": sense.id, "language_code": "en"},
            {"translated_text": word.translation, "context_note": word.teaching_note},
        )
        _provenance(
            db, source, batch, "translation",
            f"{lexical_key}:1:en:{_norm(translation.translated_text)}", version,
        )
        _upsert(
            db,
            LessonVocabulary,
            {"lesson_id": lesson.id, "lexeme_id": lexeme.id},
            {"sequence_order": order, "teaching_note": word.teaching_note},
        )
        _provenance(db, source, batch, "lesson_vocabulary", f"{data.slug}:{lexical_key}", version)
        if word.ipa:
            pronunciation = _upsert(
                db,
                Pronunciation,
                {"lexeme_id": lexeme.id, "ipa": word.ipa, "accent_variant": "standard_france"},
                {"pronunciation_notes": word.pronunciation_notes},
            )
            _provenance(
                db, source, batch, "pronunciation",
                f"{normalized}:{pronunciation.ipa}:standard_france", version,
            )
        _provenance(db, source, batch, "lexeme", lexical_key, version)

    for example in data.examples:
        sentence = _upsert(
            db,
            ExampleSentence,
            {"french_text": example.french_text, "english_translation": example.english_translation},
            {"cefr_level": "A1", "context": example.context},
        )
        for lexeme in lexemes:
            if _norm(lexeme.lemma) in _norm(example.french_text):
                _upsert(
                    db,
                    LexemeExample,
                    {"lexeme_id": lexeme.id, "example_sentence_id": sentence.id},
                    {},
                )
        _provenance(
            db, source, batch, "lexeme_example",
            f"{data.slug}:{_norm(example.french_text)}", version,
        )
        _provenance(db, source, batch, "example_sentence", f"{data.slug}:{_norm(example.french_text)}", version)

    for grammar_order, grammar in enumerate(data.grammar, start=1):
        topic = _upsert(
            db,
            GrammarTopic,
            {"slug": grammar.slug},
            {"title": grammar.title, "cefr_level": "A1", "summary": grammar.summary},
        )
        rule = _upsert(
            db,
            GrammarRule,
            {"topic_id": topic.id, "rule_code": grammar.rule_code},
            {
                "explanation_english": grammar.explanation_english,
                "explanation_french": None,
                "exceptions": None,
            },
        )
        _upsert(
            db,
            LessonGrammar,
            {"lesson_id": lesson.id, "grammar_topic_id": topic.id},
            {},
        )
        _provenance(db, source, batch, "grammar_rule", f"{grammar.slug}:{grammar.rule_code}", version)
        expected_examples = grammar_examples_by_rule[(grammar.slug, grammar.rule_code)]
        for existing in db.scalars(
            select(GrammarExample).where(GrammarExample.rule_id == rule.id)
        ).all():
            if (existing.french_sentence, existing.english_translation) not in expected_examples:
                db.delete(existing)
                COUNTER["deleted"] += 1
        for example_order, (french, english) in enumerate(grammar.examples, start=1):
            _upsert(
                db,
                GrammarExample,
                {"rule_id": rule.id, "french_sentence": french, "english_translation": english},
                {"explanation": None},
            )
            _provenance(
                db,
                source,
                batch,
                "grammar_example",
                f"{grammar.slug}:{grammar.rule_code}:{example_order}",
                version,
            )
        section_order = 20 + grammar_order
        _section(db, lesson, "grammar", grammar.title, grammar.summary, section_order)
        _provenance(db, source, batch, "lesson_section", f"{data.slug}:{section_order}", version)
        _provenance(db, source, batch, "grammar_topic", grammar.slug, version)

    dialogue = _upsert(
        db,
        Dialogue,
        {"slug": data.dialogue.slug},
        {
            "title": data.dialogue.title,
            "cefr_level": "A1",
            "context": data.dialogue.context,
            "english_context": data.dialogue.english_context,
        },
    )
    _upsert(
        db,
        LessonDialogue,
        {"lesson_id": lesson.id, "dialogue_id": dialogue.id},
        {},
    )
    for order, turn in enumerate(data.dialogue.turns, start=1):
        _upsert(
            db,
            DialogueTurn,
            {"dialogue_id": dialogue.id, "sequence_order": order},
            {
                "speaker_label": turn.speaker_label,
                "french_text": turn.french_text,
                "english_translation": turn.english_translation,
                "media_asset_id": None,
            },
        )
        _provenance(db, source, batch, "dialogue_turn", f"{dialogue.slug}:{order}", version)
    _section(db, lesson, "dialogue", data.dialogue.title, data.dialogue.english_context, 30)
    _provenance(db, source, batch, "dialogue", data.dialogue.slug, version)

    for order, exercise_data in enumerate(data.exercises, start=1):
        exercise = _upsert(
            db,
            Exercise,
            {"lesson_id": lesson.id, "sequence_order": order},
            {
                "exercise_type": exercise_data.exercise_type,
                "prompt": exercise_data.prompt,
                "instructions": exercise_data.instructions,
                "explanation": exercise_data.explanation,
                "level": "A1",
            },
        )
        for option_order, option in enumerate(exercise_data.options, start=1):
            _upsert(
                db,
                ExerciseOption,
                {"exercise_id": exercise.id, "sequence_order": option_order},
                {"option_text": option, "is_correct": option_order - 1 == exercise_data.correct_option},
            )
            _provenance(
                db, source, batch, "exercise_option",
                f"{data.slug}:{order}:{option_order}", version,
            )
        correct_answer = exercise_data.options[exercise_data.correct_option]
        _upsert(
            db,
            ExerciseAnswer,
            {"exercise_id": exercise.id},
            {
                "accepted_answer": correct_answer,
                "normalized_answer": _norm(correct_answer)[:512],
                "explanation": exercise_data.explanation,
            },
        )
        _provenance(db, source, batch, "exercise_answer", f"{data.slug}:{order}", version)
        _provenance(db, source, batch, "exercise", f"{data.slug}:{order}", version)
    _section(db, lesson, "vocabulary", "Key vocabulary", "Vocabulary is available in the linked lesson vocabulary list.", 40)
    _section(db, lesson, "practice", "Exercise preview", "Answer keys are withheld from learner responses.", 41)


def _import_reference_data(db: Session, source: ContentSource, batch: ImportBatch, version: str) -> None:
    verb_data = {
        "être": ("irregular", True, ["suis", "es", "est", "sommes", "êtes", "sont"]),
        "avoir": ("irregular", True, ["ai", "as", "a", "avons", "avez", "ont"]),
        "aller": ("irregular", True, ["vais", "vas", "va", "allons", "allez", "vont"]),
        "faire": ("irregular", True, ["fais", "fais", "fait", "faisons", "faites", "font"]),
        "parler": ("-er", False, ["parle", "parles", "parle", "parlons", "parlez", "parlent"]),
        "habiter": ("-er", False, ["habite", "habites", "habite", "habitons", "habitez", "habitent"]),
        "aimer": ("-er", False, ["aime", "aimes", "aime", "aimons", "aimez", "aiment"]),
    }
    persons = ((1, "singular"), (2, "singular"), (3, "singular"), (1, "plural"), (2, "plural"), (3, "plural"))
    for infinitive, (group, irregular, forms) in verb_data.items():
        verb = _upsert(
            db,
            VerbLemma,
            {"normalized_infinitive": _norm(infinitive)},
            {
                "infinitive": infinitive,
                "verb_group": group,
                "auxiliary": None,
                "irregular": irregular,
                "notes": "Present indicative forms for beginner reference; verify before publication.",
            },
        )
        for form, (person, number) in zip(forms, persons):
            _upsert(
                db,
                VerbConjugation,
                {
                    "verb_id": verb.id,
                    "mood": "indicative",
                    "tense": "present",
                    "grammatical_person": person,
                    "grammatical_number": number,
                },
                {"conjugated_form": form, "ipa": None},
            )
            _provenance(
                db,
                source,
                batch,
                "verb_conjugation",
                f"{_norm(infinitive)}:indicative:present:{person}:{number}",
                version,
            )
        _provenance(db, source, batch, "verb_lemma", _norm(infinitive), version)

    phonemes = (
        ("/y/", "vowel", "Close front rounded vowel.", "Round your lips while keeping the tongue forward; distinct from /u/.", "tu"),
        ("/u/", "vowel", "Close back rounded vowel.", "A back rounded vowel similar to the vowel in French tout.", "tout"),
        ("/ʁ/", "consonant", "Voiced uvular fricative or approximant.", "A French r produced at the back of the mouth; regional variants exist.", "roue"),
        ("/ɑ̃/", "vowel", "Open-mid to open nasal vowel.", "Let air pass through the nose without pronouncing a final n.", "dans"),
        ("/ɔ̃/", "vowel", "Open-mid back rounded nasal vowel.", "Keep the lips rounded and nasalize the vowel.", "bon"),
        ("/ɛ̃/", "vowel", "Open-mid front nasal vowel.", "Nasalize the vowel; do not add a separate n sound.", "pain"),
    )
    for symbol, kind, description, guide, example in phonemes:
        _upsert(
            db,
            Phoneme,
            {"ipa_symbol": symbol},
            {
                "classification": kind,
                "articulatory_description": description,
                "beginner_explanation": guide,
                "example_word": example,
            },
        )
        _provenance(db, source, batch, "phoneme", symbol, version)


def _import_data(db: Session, content: ContentImportInput) -> dict[str, int]:
    COUNTER.clear()
    content_digest = hashlib.sha256(content.model_dump_json().encode("utf-8")).hexdigest()
    grammar_examples_by_rule: dict[tuple[str, str], set[tuple[str, str]]] = {}
    for lesson in content.course.lessons:
        for grammar in lesson.grammar:
            grammar_examples_by_rule.setdefault((grammar.slug, grammar.rule_code), set()).update(
                tuple(example) for example in grammar.examples
            )
    levels = {row.code for row in db.scalars(select(CefrLevel)).all()}
    if levels != {"A1", "A2", "B1", "B2", "C1", "C2"}:
        raise ValueError("CEFR level rows are incomplete; apply Alembic revision 20261101_0003 first")

    batch_key = f"a1-starter-{content.version}"
    batch = db.scalar(select(ImportBatch).where(ImportBatch.batch_key == batch_key))
    if batch is not None and batch.report.get("_source_sha256") != content_digest:
        raise ValueError(
            f"Content changed without a version increment for {batch_key}; increment the content version."
        )

    source = _upsert(
        db,
        ContentSource,
        {"source_name": content.source_name},
        {
            "source_type": content.source_type,
            "source_url": content.source_url,
            "source_license": content.source_license,
            "attribution_requirements": content.attribution_requirements,
        },
    )
    if batch is None:
        batch = ImportBatch(
            source_id=source.id,
            batch_key=batch_key,
            content_version=content.version,
            status="running",
            report={"_source_sha256": content_digest},
        )
        db.add(batch)
        db.flush()
        COUNTER["inserted"] += 1
    else:
        batch.status = "running"

    a1 = _upsert(
        db,
        Course,
        {"slug": content.course.slug},
        {
            "level_id": "A1",
            "title": content.course.title,
            "description": content.course.description,
            "explanation_language": "en",
            "estimated_minutes": sum(lesson.estimated_minutes for lesson in content.course.lessons),
            "status": "draft",
            "content_version": content.course.version,
        },
        reopen_for_review=True,
    )
    _provenance(db, source, batch, "course", a1.slug, content.version)
    for order, title in enumerate(content.course.units, start=1):
        unit = _upsert(
            db,
            Unit,
            {"course_id": a1.id, "slug": f"a1-unit-{order:02d}"},
            {
                "title": title,
                "description": f"Draft unit {order} of the original A1 beginner course.",
                "sequence_order": order,
                "status": "draft",
            },
            reopen_for_review=True,
        )
        _provenance(db, source, batch, "unit", unit.slug, content.version)
        for lesson_data in content.course.lessons[(order - 1) * 2 : order * 2]:
            _import_lesson(
                db,
                source,
                batch,
                lesson_data,
                unit,
                int(lesson_data.slug[-3:]) - (order - 1) * 2,
                content.version,
                grammar_examples_by_rule,
            )

    for planned in content.planned_courses:
        course = _upsert(
            db,
            Course,
            {"slug": planned.slug},
            {
                "level_id": planned.level,
                "title": planned.title,
                "description": planned.description,
                "explanation_language": "en",
                "estimated_minutes": 0,
                "status": "draft",
                "content_version": content.version,
            },
            reopen_for_review=True,
        )
        _provenance(db, source, batch, "course", course.slug, content.version)
        for order, title in enumerate(planned.unit_titles, start=1):
            slug = f"{planned.slug}-unit-{order:02d}"
            unit = _upsert(
                db,
                Unit,
                {"course_id": course.id, "slug": slug},
                {
                    "title": title,
                    "description": "Planned curriculum outline; lesson content is not yet available.",
                    "sequence_order": order,
                    "status": "draft",
                },
                reopen_for_review=True,
            )
            _provenance(db, source, batch, "unit", slug, content.version)
        for skill in ("listening", "speaking", "reading", "writing", "vocabulary", "grammar"):
            code = f"{planned.level.lower()}-outline-{skill}"
            objective = _objective(
                db,
                {
                    "code": code,
                    "title": f"{planned.level} {skill.title()} — planned",
                    "description": planned.description,
                    "skill_category": skill,
                },
                planned.level,
            )
            _provenance(db, source, batch, "learning_objective", objective.code, content.version)

    _import_reference_data(db, source, batch, content.version)
    db.flush()
    report = {name: COUNTER[name] for name in ("inserted", "updated", "deleted", "unchanged")}
    report.update(
        {
            "a1_draft_lessons": len(content.course.lessons),
            "published_lessons": 0,
            "planned_level_courses": len(content.planned_courses),
            "lexeme_entries_in_source": sum(len(lesson.vocabulary) for lesson in content.course.lessons),
            "exercise_items_in_source": sum(len(lesson.exercises) for lesson in content.course.lessons),
            "rejected": 0,
            "_source_sha256": content_digest,
        }
    )
    batch.status = "completed"
    batch.report = report
    db.flush()
    return report


def load_content(path: Path) -> ContentImportInput:
    try:
        return ContentImportInput.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as error:
        details = "\n".join(f"{path}: {item['loc']}: {item['msg']}" for item in error.errors())
        raise ContentSourceError(details) from error
    except OSError as error:
        raise ContentSourceError(f"{path}: {error}") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or import the FluentLoop A1 draft curriculum.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--validate-only", action="store_true", help="Validate source content without writing.")
    mode.add_argument("--dry-run", action="store_true", help="Validate and show the planned import without writing.")
    mode.add_argument("--apply", action="store_true", help="Import validated content transactionally.")
    parser.add_argument("--content", type=Path, default=CONTENT_PATH, help="JSON curriculum source file.")
    args = parser.parse_args(argv)
    try:
        content = load_content(args.content)
        counts = {
            "a1_draft_lessons": len(content.course.lessons),
            "vocabulary_entries": sum(len(lesson.vocabulary) for lesson in content.course.lessons),
            "exercise_items": sum(len(lesson.exercises) for lesson in content.course.lessons),
            "planned_level_courses": len(content.planned_courses),
            "published_lessons": 0,
            "rejected": 0,
        }
        if args.apply:
            with SessionLocal.begin() as db:
                counts = _import_data(db, content)
        print(json.dumps({"status": "valid" if not args.apply else "imported", "counts": counts}, ensure_ascii=False, indent=2))
        return 0
    except ContentSourceError as error:
        print(
            json.dumps(
                {"status": "rejected", "counts": {"rejected": 1}, "errors": str(error).splitlines()},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    except (ValueError, ValidationError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
