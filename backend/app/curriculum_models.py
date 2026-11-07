from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


LEVEL_CHECK = "cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')"
STRUCTURED_JSON = JSON().with_variant(JSONB, "postgresql")


class CefrLevel(Base):
    __tablename__ = "cefr_levels"
    __table_args__ = (
        CheckConstraint("code IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')", name="ck_cefr_levels_code"),
        CheckConstraint("rank BETWEEN 1 AND 6", name="ck_cefr_levels_rank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class ContentSource(Base):
    __tablename__ = "content_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    source_name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    source_license: Mapped[str] = mapped_column(String(160), nullable=False)
    attribution_requirements: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class ImportBatch(Base):
    __tablename__ = "content_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("content_sources.id"), nullable=False)
    batch_key: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="validated")
    report: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class ContentProvenance(Base):
    __tablename__ = "content_provenance"
    __table_args__ = (
        UniqueConstraint("item_type", "item_key", "content_version", name="uq_provenance_item_version"),
        CheckConstraint(
            "review_state IN ('draft', 'automated_checked', 'human_reviewed', 'rejected', 'published')",
            name="ck_provenance_review_state",
        ),
        Index("ix_content_provenance_item", "item_type", "item_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    item_type: Mapped[str] = mapped_column(String(48), nullable=False)
    item_key: Mapped[str] = mapped_column(String(200), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("content_sources.id"), nullable=False)
    import_batch_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("content_import_batches.id"), nullable=False)
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(24), nullable=False)
    review_state: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    review_metadata: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'review', 'published', 'archived')", name="ck_courses_status"),
        Index("ix_courses_level_status", "level_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    level_id: Mapped[str] = mapped_column(String(2), ForeignKey("cefr_levels.code"), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("course_id", "slug", name="uq_units_course_slug"),
        UniqueConstraint("course_id", "sequence_order", name="uq_units_course_order"),
        CheckConstraint("status IN ('draft', 'review', 'published', 'archived')", name="ck_units_status"),
        Index("ix_units_course_order", "course_id", "sequence_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    course_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        UniqueConstraint("unit_id", "slug", name="uq_lessons_unit_slug"),
        UniqueConstraint("unit_id", "sequence_order", name="uq_lessons_unit_order"),
        CheckConstraint("difficulty_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')", name="ck_lessons_difficulty_level"),
        CheckConstraint("status IN ('draft', 'review', 'published', 'archived')", name="ck_lessons_status"),
        Index("ix_lessons_unit_order", "unit_id", "sequence_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    unit_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty_level: Mapped[str] = mapped_column(String(2), nullable=False)
    explanation_language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class LessonSection(Base):
    __tablename__ = "lesson_sections"
    __table_args__ = (
        UniqueConstraint("lesson_id", "sequence_order", name="uq_lesson_sections_order"),
        CheckConstraint(
            "section_type IN ('introduction', 'explanation', 'vocabulary', 'grammar', 'dialogue', 'pronunciation', 'practice', 'recap')",
            name="ck_lesson_sections_type",
        ),
        Index("ix_lesson_sections_lesson_order", "lesson_id", "sequence_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    lesson_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    section_type: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body_content: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content_metadata: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    __table_args__ = (
        CheckConstraint("level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')", name="ck_objectives_level"),
        CheckConstraint(
            "skill_category IN ('listening', 'speaking', 'reading', 'writing', 'vocabulary', 'grammar')",
            name="ck_objectives_skill",
        ),
        Index("ix_objectives_level_skill", "level", "skill_category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    level: Mapped[str] = mapped_column(String(2), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skill_category: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class LessonObjective(Base):
    __tablename__ = "lesson_objectives"

    lesson_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    objective_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("learning_objectives.id", ondelete="CASCADE"), primary_key=True)


class Lexeme(Base):
    __tablename__ = "lexemes"
    __table_args__ = (
        CheckConstraint("part_of_speech IN ('noun', 'verb', 'adjective', 'adverb', 'pronoun', 'article', 'preposition', 'conjunction', 'interjection', 'phrase')", name="ck_lexemes_part_of_speech"),
        Index("ix_lexemes_normalized_lemma", "normalized_lemma"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    lemma: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_lemma: Mapped[str] = mapped_column(String(160), nullable=False)
    part_of_speech: Mapped[str] = mapped_column(String(24), nullable=False)
    grammatical_gender: Mapped[Optional[str]] = mapped_column(String(16))
    irregularity_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class WordSense(Base):
    __tablename__ = "word_senses"
    __table_args__ = (UniqueConstraint("lexeme_id", "sense_number", name="uq_word_senses_number"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    lexeme_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False)
    sense_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_french: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_english: Mapped[str] = mapped_column(Text, nullable=False)
    usage_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class Translation(Base):
    __tablename__ = "translations"
    __table_args__ = (UniqueConstraint("word_sense_id", "language_code", "translated_text", name="uq_translations_sense_language_text"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    word_sense_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("word_senses.id", ondelete="CASCADE"), nullable=False)
    language_code: Mapped[str] = mapped_column(String(8), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    context_note: Mapped[Optional[str]] = mapped_column(Text)


class ExampleSentence(Base):
    __tablename__ = "example_sentences"
    __table_args__ = (CheckConstraint(LEVEL_CHECK, name="ck_examples_level"), Index("ix_examples_level", "cefr_level"))

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    french_text: Mapped[str] = mapped_column(Text, nullable=False)
    english_translation: Mapped[str] = mapped_column(Text, nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    context: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class LexemeExample(Base):
    __tablename__ = "lexeme_examples"

    lexeme_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lexemes.id", ondelete="CASCADE"), primary_key=True)
    example_sentence_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("example_sentences.id", ondelete="CASCADE"), primary_key=True)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    license_identifier: Mapped[str] = mapped_column(String(160), nullable=False)
    attribution: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class Pronunciation(Base):
    __tablename__ = "pronunciations"
    __table_args__ = (UniqueConstraint("lexeme_id", "ipa", "accent_variant", name="uq_pronunciation_variant"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    lexeme_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lexemes.id", ondelete="CASCADE"), nullable=False)
    ipa: Mapped[str] = mapped_column(String(160), nullable=False)
    accent_variant: Mapped[str] = mapped_column(String(80), nullable=False, default="standard_france")
    media_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("media_assets.id"))
    pronunciation_notes: Mapped[Optional[str]] = mapped_column(Text)


class LessonVocabulary(Base):
    __tablename__ = "lesson_vocabulary"
    __table_args__ = (
        UniqueConstraint("lesson_id", "sequence_order", name="uq_lesson_vocabulary_order"),
        UniqueConstraint("lesson_id", "lexeme_id", name="uq_lesson_vocabulary_lexeme"),
    )

    lesson_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    lexeme_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lexemes.id", ondelete="CASCADE"), primary_key=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    teaching_note: Mapped[Optional[str]] = mapped_column(Text)


class GrammarTopic(Base):
    __tablename__ = "grammar_topics"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_grammar_topics_slug"),
        CheckConstraint("cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')", name="ck_grammar_topics_level"),
        Index("ix_grammar_topics_level", "cefr_level"),
        CheckConstraint("publication_status IN ('inherited','draft','review','published','retired')", name="ck_grammar_topic_publication"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    publication_status: Mapped[str] = mapped_column(String(24), nullable=False, default="inherited", server_default="inherited")
    teaching_metadata: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class GrammarRule(Base):
    __tablename__ = "grammar_rules"
    __table_args__ = (UniqueConstraint("topic_id", "rule_code", name="uq_grammar_rule_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    topic_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("grammar_topics.id", ondelete="CASCADE"), nullable=False)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation_english: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_french: Mapped[Optional[str]] = mapped_column(Text)
    exceptions: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class GrammarExample(Base):
    __tablename__ = "grammar_examples"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    rule_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("grammar_rules.id", ondelete="CASCADE"), nullable=False)
    french_sentence: Mapped[str] = mapped_column(Text, nullable=False)
    english_translation: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text)


class LessonGrammar(Base):
    __tablename__ = "lesson_grammar"

    lesson_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    grammar_topic_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("grammar_topics.id", ondelete="CASCADE"), primary_key=True)


class VerbLemma(Base):
    __tablename__ = "verb_lemmas"
    __table_args__ = (Index("ix_verb_lemmas_normalized", "normalized_infinitive", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    infinitive: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_infinitive: Mapped[str] = mapped_column(String(120), nullable=False)
    verb_group: Mapped[str] = mapped_column(String(32), nullable=False)
    auxiliary: Mapped[Optional[str]] = mapped_column(String(8))
    irregular: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)


class VerbConjugation(Base):
    __tablename__ = "verb_conjugations"
    __table_args__ = (
        UniqueConstraint("verb_id", "mood", "tense", "grammatical_person", "grammatical_number", name="uq_verb_conjugation_identity"),
        CheckConstraint("grammatical_person BETWEEN 1 AND 3", name="ck_conjugation_person"),
        CheckConstraint("grammatical_number IN ('singular', 'plural')", name="ck_conjugation_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    verb_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("verb_lemmas.id", ondelete="CASCADE"), nullable=False)
    mood: Mapped[str] = mapped_column(String(32), nullable=False)
    tense: Mapped[str] = mapped_column(String(32), nullable=False)
    grammatical_person: Mapped[int] = mapped_column(Integer, nullable=False)
    grammatical_number: Mapped[str] = mapped_column(String(8), nullable=False)
    conjugated_form: Mapped[str] = mapped_column(String(160), nullable=False)
    ipa: Mapped[Optional[str]] = mapped_column(String(160))


class Phoneme(Base):
    __tablename__ = "phonemes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    ipa_symbol: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    articulatory_description: Mapped[str] = mapped_column(Text, nullable=False)
    beginner_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    example_word: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class Dialogue(Base):
    __tablename__ = "dialogues"
    __table_args__ = (
        CheckConstraint("cefr_level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')", name="ck_dialogues_level"),
        Index("ix_dialogues_level", "cefr_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    cefr_level: Mapped[str] = mapped_column(String(2), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    english_context: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class DialogueTurn(Base):
    __tablename__ = "dialogue_turns"
    __table_args__ = (UniqueConstraint("dialogue_id", "sequence_order", name="uq_dialogue_turn_order"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    dialogue_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dialogues.id", ondelete="CASCADE"), nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(80), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    french_text: Mapped[str] = mapped_column(Text, nullable=False)
    english_translation: Mapped[str] = mapped_column(Text, nullable=False)
    media_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("media_assets.id"))


class LessonDialogue(Base):
    __tablename__ = "lesson_dialogues"

    lesson_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True)
    dialogue_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("dialogues.id", ondelete="CASCADE"), primary_key=True)


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint("exercise_type IN ('multiple_choice', 'translation', 'fill_blank', 'matching', 'sentence_order', 'short_answer', 'listening')", name="ck_exercises_type"),
        CheckConstraint("level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')", name="ck_exercises_level"),
        UniqueConstraint("lesson_id", "sequence_order", name="uq_exercises_lesson_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    lesson_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    exercise_type: Mapped[str] = mapped_column(String(24), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(2), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    exercise_data: Mapped[dict] = mapped_column(STRUCTURED_JSON, nullable=False, default=dict, server_default=text("'{}'"))
    learning_objective_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("learning_objectives.id", ondelete="RESTRICT"))
    grammar_topic_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), ForeignKey("grammar_topics.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class ExerciseOption(Base):
    __tablename__ = "exercise_options"
    __table_args__ = (UniqueConstraint("exercise_id", "sequence_order", name="uq_exercise_options_order"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    exercise_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ExerciseAnswer(Base):
    __tablename__ = "exercise_answers"
    __table_args__ = (UniqueConstraint("exercise_id", "accepted_answer", name="uq_exercise_answer"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    exercise_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False)
    accepted_answer: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_answer: Mapped[str] = mapped_column(String(512), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
