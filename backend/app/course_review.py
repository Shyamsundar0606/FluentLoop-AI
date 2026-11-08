"""Versioned independent curriculum review backed by existing provenance."""
import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from app.config import ReviewCategory
from app.services.exercise_formats import definition
from app.services.grading_service import normalize_written
from app.curriculum_models import (
    ContentProvenance, ContentSource, Dialogue, DialogueTurn, Exercise, ExerciseOption, GrammarExample,
    GrammarRule, GrammarTopic, Lesson, LessonGrammar, LessonObjective, LessonSection,
    LessonDialogue, LessonVocabulary, LearningObjective, Lexeme, Pronunciation, Translation, Unit, WordSense,
    VerbConjugation, VerbLemma,
)

CATEGORIES = ("linguistic_accuracy", "phonetics", "pedagogy", "answer_keys", "licensing")


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    version: str = Field(min_length=1, max_length=32)
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    category: ReviewCategory
    status: Literal["approved", "changes_requested"]
    findings: str = Field(min_length=8, max_length=4000)
    required_corrections: str = Field(default="", max_length=4000)
    evidence: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def check_decision(self):
        if (self.status == "changes_requested") != bool(self.required_corrections):
            raise ValueError("Required corrections must accompany a changes-requested decision")
        if self.category == "licensing" and self.status == "approved" and not self.evidence:
            raise ValueError("Licensing approval requires evidence")
        return self


def provenance(db, course, *, lock=False):
    query = select(ContentProvenance).where(
        ContentProvenance.item_type == "course", ContentProvenance.item_key == course.slug,
        ContentProvenance.content_version == course.content_version,
    )
    return db.scalar(query.with_for_update() if lock else query)


def _rows(db, statement):
    return [dict(row) for row in db.execute(statement).mappings()]


def packet(db, course, source):
    lessons = []
    for unit in db.scalars(select(Unit).where(Unit.course_id == course.id).order_by(Unit.sequence_order)):
        for lesson in db.scalars(select(Lesson).where(Lesson.unit_id == unit.id).order_by(Lesson.sequence_order)):
            lid = lesson.id
            sections = _rows(db, select(LessonSection.title, LessonSection.section_type, LessonSection.body_content,
                LessonSection.content_metadata).where(LessonSection.lesson_id == lid).order_by(LessonSection.sequence_order))
            objectives = _rows(db, select(LearningObjective.code, LearningObjective.title, LearningObjective.description)
                .join(LessonObjective).where(LessonObjective.lesson_id == lid).order_by(LearningObjective.code))
            vocabulary = []
            for word, note in db.execute(select(Lexeme, LessonVocabulary.teaching_note).join(LessonVocabulary)
                .where(LessonVocabulary.lesson_id == lid).order_by(LessonVocabulary.sequence_order)):
                vocabulary.append(dict(word=word.lemma, gender=word.grammatical_gender, part=word.part_of_speech, note=note,
                    definitions=_rows(db, select(WordSense.definition_french, WordSense.explanation_english,
                        WordSense.usage_notes).where(WordSense.lexeme_id == word.id).order_by(WordSense.sense_number)),
                    translations=_rows(db, select(Translation.translated_text, Translation.language_code)
                        .join(WordSense).where(WordSense.lexeme_id == word.id)
                        .order_by(WordSense.sense_number, Translation.language_code, Translation.translated_text)),
                    pronunciation=_rows(db, select(Pronunciation.ipa, Pronunciation.accent_variant)
                        .where(Pronunciation.lexeme_id == word.id).order_by(Pronunciation.ipa, Pronunciation.accent_variant))))
                if word.part_of_speech == "verb":
                    vocabulary[-1]["conjugation"] = _rows(db, select(VerbConjugation.mood, VerbConjugation.tense,
                        VerbConjugation.grammatical_person, VerbConjugation.grammatical_number, VerbConjugation.conjugated_form)
                        .join(VerbLemma).where(VerbLemma.normalized_infinitive == word.normalized_lemma)
                        .order_by(VerbConjugation.mood, VerbConjugation.tense, VerbConjugation.grammatical_number,
                                  VerbConjugation.grammatical_person))
            grammar = []
            for topic in db.scalars(select(GrammarTopic).join(LessonGrammar).where(LessonGrammar.lesson_id == lid)
                .order_by(GrammarTopic.slug)):
                metadata = topic.teaching_metadata
                rules = []
                for rule in db.scalars(select(GrammarRule).where(GrammarRule.topic_id == topic.id)
                    .order_by(GrammarRule.rule_code)):
                    if metadata.get("curriculum_supplement") and (
                        (rule.rule_code == metadata["rule_code"]) != (lesson.slug == metadata["preferred_lesson_slug"])
                    ):
                        continue
                    rules.append(dict(code=rule.rule_code, explanation=rule.explanation_english,
                        explanation_french=rule.explanation_french, exceptions=rule.exceptions, examples=_rows(db, select(GrammarExample.french_sentence,
                            GrammarExample.english_translation).where(GrammarExample.rule_id == rule.id)
                            .order_by(GrammarExample.french_sentence, GrammarExample.english_translation))))
                grammar.append(dict(slug=topic.slug, title=topic.title, summary=topic.summary, rules=rules,
                    teaching=metadata if metadata.get("preferred_lesson_slug") == lesson.slug else {}))
            exercises = []
            for exercise in db.scalars(select(Exercise).where(Exercise.lesson_id == lid).order_by(Exercise.sequence_order)):
                exercises.append(dict(id=str(exercise.id), type=exercise.exercise_type, level=exercise.level, prompt=exercise.prompt,
                    instructions=exercise.instructions, feedback=exercise.explanation, data=exercise.exercise_data,
                    objective=str(exercise.learning_objective_id or ""), grammar=str(exercise.grammar_topic_id or ""),
                    options=_rows(db, select(ExerciseOption.option_text, ExerciseOption.is_correct)
                        .where(ExerciseOption.exercise_id == exercise.id).order_by(ExerciseOption.sequence_order))))
            dialogues = []
            for dialogue in db.scalars(select(Dialogue).join(LessonDialogue).where(LessonDialogue.lesson_id == lid)
                .order_by(Dialogue.slug)):
                turns = _rows(db, select(DialogueTurn.speaker_label, DialogueTurn.french_text,
                    DialogueTurn.english_translation).where(DialogueTurn.dialogue_id == dialogue.id)
                    .order_by(DialogueTurn.sequence_order))
                dialogues.append(dict(slug=dialogue.slug, title=dialogue.title, level=dialogue.cefr_level,
                    context=dialogue.context, english_context=dialogue.english_context, turns=turns))
            lessons.append(dict(slug=lesson.slug, title=lesson.title, description=lesson.description,
                version=lesson.content_version, level=lesson.difficulty_level, order=[unit.sequence_order, lesson.sequence_order],
                unit_title=unit.title, estimated_minutes=lesson.estimated_minutes,
                sections=sections, objectives=objectives, vocabulary=vocabulary, grammar=grammar,
                dialogues=dialogues, exercises=exercises))
    content_source = db.get(ContentSource, source.source_id)
    return dict(course=course.slug, title=course.title, description=course.description,
        version=course.content_version, level=course.level_id, source_type=content_source.source_type,
        source_url=content_source.source_url, source_license=content_source.source_license,
        attribution=content_source.attribution_requirements, lessons=lessons)


def digest_packet(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_packet(content):
    issues = []
    if not content["lessons"] or not content["source_license"] or not content["attribution"]:
        issues.append("Missing lesson content or source provenance.")
    if content["level"] != "A1":
        issues.append("Review packets currently require A1.")
    orders = [lesson["order"] for lesson in content["lessons"]]
    if orders != sorted(orders) or len({tuple(order) for order in orders}) != len(orders):
        issues.append("Lesson order must be unique and increasing.")
    for lesson in content["lessons"]:
        slug = lesson["slug"]
        if lesson["version"] != content["version"] or lesson["level"] != content["level"]:
            issues.append(f"{slug}: lesson version or level differs from course.")
        if any(not lesson[field] for field in ("title", "description", "sections", "objectives", "grammar", "exercises")):
            issues.append(f"{slug}: incomplete lesson packet.")
        for word in lesson["vocabulary"]:
            if not any(t["language_code"] == "en" and t["translated_text"].strip() for t in word["translations"]):
                issues.append(f"{slug}: vocabulary item lacks an English translation.")
        words = {(w["word"].casefold(), w["part"], w["gender"]) for w in lesson["vocabulary"]}
        if len(words) != len(lesson["vocabulary"]):
            issues.append(f"{slug}: duplicate vocabulary identity.")
        for topic in lesson["grammar"]:
            if not topic["rules"] or any(not rule["explanation"] or any(
                not example["french_sentence"] or not example["english_translation"]
                for example in rule["examples"]) for rule in topic["rules"]):
                issues.append(f"{slug}: incomplete grammar examples or explanation.")
        for number, exercise in enumerate(lesson["exercises"], 1):
            try:
                if exercise["level"] != lesson["level"]:
                    raise ValueError("exercise and lesson levels differ")
                definition(exercise["type"], exercise["data"])
                if exercise["type"] in ("multiple_choice", "listening"):
                    labels = [normalize_written(option["option_text"]) for option in exercise["options"]]
                    if len(labels) < 2 or "" in labels or len(set(labels)) != len(labels):
                        raise ValueError("invalid choices")
                    if sum(option["is_correct"] for option in exercise["options"]) != 1:
                        raise ValueError("one answer key required")
                elif "accepted_answers" in exercise["data"]:
                    variants = [normalize_written(answer) for answer in exercise["data"]["accepted_answers"]]
                    if "" in variants or len(set(variants)) != len(variants):
                        raise ValueError("invalid written variants")
            except ValueError:
                issues.append(f"{slug}: exercise {number} has an invalid definition or key.")
    raw = json.dumps(content, ensure_ascii=False)
    if unicodedata.normalize("NFC", raw) != raw or "\ufffd" in raw:
        issues.append("Content contains non-NFC or replacement Unicode characters.")
    return issues


def readiness(history, digest, version):
    decisions = {(entry["category"], entry["reviewer_id"]): entry for entry in history
                 if entry["digest"] == digest and entry["version"] == version}
    statuses = {category: {entry["status"] for (key, _), entry in decisions.items() if key == category}
                for category in CATEGORIES}
    outstanding = [category for category, values in statuses.items() if values != {"approved"}]
    other_reviewers = {reviewer for (category, reviewer) in decisions if category != "licensing"}
    independent_licensing = any(
        category == "licensing" and reviewer not in other_reviewers and entry.get("evidence")
        and entry["status"] == "approved" for (category, reviewer), entry in decisions.items()
    )
    return dict(outstanding=outstanding, independent_licensing=independent_licensing,
                complete=not outstanding and independent_licensing)


def record_review(source, payload, reviewer_id: UUID, grant):
    history = source.review_metadata.get("independent_reviews", [])
    entry = {**payload.model_dump(), "reviewer_id": str(reviewer_id),
             "qualification": grant.qualification, "reviewed_at": datetime.now(timezone.utc).isoformat()}
    source.review_metadata = {**source.review_metadata, "independent_reviews": [*history, entry]}
    return entry
