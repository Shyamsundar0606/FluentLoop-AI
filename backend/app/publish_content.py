from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.content_schemas import A1PublicationReviewRecord
from app.curriculum_models import (
    ContentProvenance,
    Course,
    Dialogue,
    Exercise,
    ExerciseOption,
    GrammarTopic,
    Lesson,
    LessonDialogue,
    LessonGrammar,
    LessonObjective,
    LessonSection,
    LessonVocabulary,
    LearningObjective,
    Lexeme,
    Pronunciation,
    Unit,
    ImportBatch,
)


def publish_course(
    db: Session,
    review_record: A1PublicationReviewRecord | dict[str, Any],
) -> dict[str, int]:
    review = A1PublicationReviewRecord.model_validate(review_record)
    course_slug = review.course_slug
    course = db.scalar(select(Course).where(Course.slug == course_slug))
    if course is None:
        raise ValueError(f"Course not found: {course_slug}")
    if course.level_id != "A1":
        raise ValueError("This publication command is scoped to the authored A1 starter course.")

    units = db.scalars(select(Unit).where(Unit.course_id == course.id).order_by(Unit.sequence_order)).all()
    lessons = db.scalars(
        select(Lesson)
        .join(Unit, Lesson.unit_id == Unit.id)
        .where(Unit.course_id == course.id)
        .order_by(Unit.sequence_order, Lesson.sequence_order)
    ).all()
    if not units or len(lessons) != 10:
        raise ValueError("The A1 course must contain all ten starter lessons before publication.")
    expected_lesson_slugs = {f"a1-{number:03d}" for number in range(1, 11)}
    if {lesson.slug for lesson in lessons} != expected_lesson_slugs:
        raise ValueError("The A1 course must contain lessons a1-001 through a1-010.")
    if any(lesson.difficulty_level != "A1" for lesson in lessons):
        raise ValueError("A1 course contains a lesson with a different CEFR difficulty.")
    if course.content_version != review.content_version:
        raise ValueError("Review record content version does not match the current course.")
    if {item.lesson_slug for item in review.lessons} != expected_lesson_slugs:
        raise ValueError("Review record must approve every current A1 lesson exactly once.")
    licensing_reviewer = review.license_and_attribution.reviewer.strip().casefold()
    lesson_reviewers = {
        approval.reviewer.strip().casefold()
        for item in review.lessons
        for approval in (item.french_language, item.pedagogy_and_sequence, item.exercise_answers)
    }
    if licensing_reviewer in lesson_reviewers:
        raise ValueError("License and attribution approval must come from a separate human reviewer.")

    lesson_ids = [lesson.id for lesson in lessons]
    lesson_slugs = {lesson.slug for lesson in lessons}
    unit_slugs = {unit.slug for unit in units}
    objective_codes = set(
        db.scalars(
            select(LearningObjective.code)
            .join(LessonObjective, LearningObjective.id == LessonObjective.objective_id)
            .where(LessonObjective.lesson_id.in_(lesson_ids))
        ).all()
    )
    lexemes = db.scalars(
        select(Lexeme)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == Lexeme.id)
        .where(LessonVocabulary.lesson_id.in_(lesson_ids))
        .distinct()
    ).all()
    lexeme_keys = {
        f"{lexeme.normalized_lemma}:{lexeme.part_of_speech}:{lexeme.grammatical_gender or ''}"
        for lexeme in lexemes
    }
    verb_keys = {
        lexeme.normalized_lemma
        for lexeme in lexemes
        if lexeme.part_of_speech == "verb"
    }
    pronunciation_keys = {
        f"{lexeme.normalized_lemma}:{pronunciation.ipa}:standard_france"
        for lexeme in lexemes
        for pronunciation in db.scalars(
            select(Pronunciation).where(Pronunciation.lexeme_id == lexeme.id)
        ).all()
    }
    grammar_slugs = set(
        db.scalars(
            select(GrammarTopic.slug)
            .join(LessonGrammar, LessonGrammar.grammar_topic_id == GrammarTopic.id)
            .where(LessonGrammar.lesson_id.in_(lesson_ids))
        ).all()
    )
    dialogue_slugs = set(
        db.scalars(
            select(Dialogue.slug)
            .join(LessonDialogue, LessonDialogue.dialogue_id == Dialogue.id)
            .where(LessonDialogue.lesson_id.in_(lesson_ids))
        ).all()
    )
    exercise_keys = {
        f"{lesson.slug}:{order}"
        for lesson in lessons
        for order in db.scalars(
            select(Exercise.sequence_order).where(Exercise.lesson_id == lesson.id)
        ).all()
    }
    section_keys = {
        f"{lesson.slug}:{order}"
        for lesson in lessons
        for order in db.scalars(
            select(LessonSection.sequence_order).where(LessonSection.lesson_id == lesson.id)
        ).all()
    }

    for lesson in lessons:
        options = db.scalars(select(ExerciseOption).join(Exercise).where(Exercise.lesson_id == lesson.id)).all()
        exercises = db.scalars(select(Exercise).where(Exercise.lesson_id == lesson.id)).all()
        if len(exercises) < 5:
            raise ValueError(f"{lesson.slug}: at least five exercises are required.")
        for exercise in exercises:
            exercise_options = [option for option in options if option.exercise_id == exercise.id]
            if exercise.exercise_type == "multiple_choice" and sum(option.is_correct for option in exercise_options) != 1:
                raise ValueError(f"{lesson.slug}: each multiple-choice exercise must have exactly one correct option.")

    batch = db.scalar(
        select(ImportBatch)
        .join(ContentProvenance, ContentProvenance.import_batch_id == ImportBatch.id)
        .where(
            ContentProvenance.item_type == "course",
            ContentProvenance.item_key == course_slug,
            ImportBatch.content_version == course.content_version,
            ImportBatch.status == "completed",
        )
        .order_by(ImportBatch.created_at.desc())
    )
    if batch is None:
        raise ValueError("Course provenance is missing; re-import validated source content first.")
    source_digest = batch.report.get("_source_sha256")
    if source_digest != review.source_sha256:
        raise ValueError("Review record source digest does not match the imported course content.")
    all_provenance = db.scalars(
        select(ContentProvenance).where(
            ContentProvenance.import_batch_id == batch.id,
            ContentProvenance.validation_status == "passed",
        )
    ).all()
    allowed_keys = {
        ("course", course.slug),
        *[("unit", slug) for slug in unit_slugs],
        *[("lesson", slug) for slug in lesson_slugs],
        *[("learning_objective", code) for code in objective_codes],
        *[("lexeme", key) for key in lexeme_keys],
        *[("pronunciation", key) for key in pronunciation_keys],
        *[("grammar_topic", slug) for slug in grammar_slugs],
        *[("dialogue", slug) for slug in dialogue_slugs],
        *[("exercise", key) for key in exercise_keys],
        *[("lesson_section", key) for key in section_keys],
    }
    lesson_prefixes = tuple(f"{slug}:" for slug in lesson_slugs)
    lexical_prefixes = tuple(f"{key}:" for key in lexeme_keys)
    grammar_prefixes = tuple(f"{slug}:" for slug in grammar_slugs)
    dialogue_prefixes = tuple(f"{slug}:" for slug in dialogue_slugs)

    def belongs_to_a1_course(row: ContentProvenance) -> bool:
        if (row.item_type, row.item_key) in allowed_keys:
            return True
        if row.item_type in {"word_sense", "translation"}:
            return row.item_key.startswith(lexical_prefixes)
        if row.item_type in {"lesson_vocabulary", "lexeme_example", "exercise_option", "exercise_answer"}:
            return row.item_key.startswith(lesson_prefixes)
        if row.item_type in {"grammar_rule", "grammar_example"}:
            return row.item_key.startswith(grammar_prefixes)
        if row.item_type == "dialogue_turn":
            return row.item_key.startswith(dialogue_prefixes)
        if row.item_type == "verb_conjugation":
            return row.item_key.startswith(tuple(f"{key}:" for key in verb_keys))
        return row.item_type == "phoneme"

    provenance_rows = [row for row in all_provenance if belongs_to_a1_course(row)]
    if not provenance_rows:
        raise ValueError("No validated provenance records are available for this course.")

    course.status = "published"
    for unit in units:
        unit.status = "published"
    for lesson in lessons:
        lesson.status = "published"

    review_data = review.model_dump(mode="json")
    review_metadata: dict[str, Any] = {
        "review_record_sha256": hashlib.sha256(
            review.model_dump_json().encode("utf-8")
        ).hexdigest(),
        "review_record": review_data,
        "independent_human_review": True,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }
    for provenance in provenance_rows:
        provenance.review_state = "published"
        provenance.review_metadata = review_metadata

    return {
        "courses_published": 1,
        "units_published": len(units),
        "lessons_published": len(lessons),
        "provenance_records_updated": len(provenance_rows),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publish A1 only after validating a complete independent human-review record."
    )
    parser.add_argument(
        "--review-record",
        required=True,
        type=Path,
        help="Admin-prepared JSON record containing independent language, pedagogy, answer, and licensing approvals.",
    )
    args = parser.parse_args(argv)
    try:
        review_record = A1PublicationReviewRecord.model_validate_json(
            args.review_record.read_text(encoding="utf-8")
        )
        with SessionLocal.begin() as db:
            result = publish_course(db, review_record)
        print(json.dumps({"status": "published", **result}, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ValidationError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
