from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CEFR = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
Skill = Literal["listening", "speaking", "reading", "writing", "vocabulary", "grammar"]
PartOfSpeech = Literal[
    "noun", "verb", "adjective", "adverb", "pronoun", "article",
    "preposition", "conjunction", "interjection", "phrase",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ObjectiveInput(StrictModel):
    code: str = Field(min_length=3, max_length=80)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=8)
    skill_category: Skill


class VocabularyInput(StrictModel):
    lemma: str = Field(min_length=1, max_length=160)
    part_of_speech: PartOfSpeech
    grammatical_gender: Literal["masculine", "feminine"] | None = None
    translation: str = Field(min_length=1)
    definition_french: str = Field(min_length=1)
    irregularity_notes: str | None = None
    teaching_note: str | None = None
    ipa: str | None = None
    pronunciation_notes: str | None = None

    @model_validator(mode="after")
    def preserve_normalizable_unicode(self) -> "VocabularyInput":
        if self.lemma != unicodedata.normalize("NFC", self.lemma):
            raise ValueError("lemma must use Unicode NFC normalization; do not strip French diacritics")
        return self


class ExampleInput(StrictModel):
    french_text: str = Field(min_length=1)
    english_translation: str = Field(min_length=1)
    context: str | None = None

class GrammarInput(StrictModel):
    slug: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=3, max_length=200)
    summary: str = Field(min_length=8)
    rule_code: str = Field(min_length=2, max_length=100)
    explanation_english: str = Field(min_length=8)
    examples: list[tuple[str, str]] = Field(min_length=1)


class DialogueTurnInput(StrictModel):
    speaker_label: str = Field(min_length=1, max_length=80)
    french_text: str = Field(min_length=1)
    english_translation: str = Field(min_length=1)


class DialogueInput(StrictModel):
    slug: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=200)
    context: str = Field(min_length=4)
    english_context: str = Field(min_length=4)
    turns: list[DialogueTurnInput] = Field(min_length=2)


class ExerciseInput(StrictModel):
    exercise_type: Literal[
        "multiple_choice", "translation", "fill_blank",
        "matching", "sentence_order", "short_answer",
    ]
    prompt: str = Field(min_length=4)
    instructions: str = Field(min_length=4)
    explanation: str = Field(min_length=4)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_option: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_answer_key(self) -> "ExerciseInput":
        if self.correct_option >= len(self.options):
            raise ValueError("correct_option must reference an existing option")
        if len(set(self.options)) != len(self.options):
            raise ValueError("exercise options must be unique")
        return self


class LessonInput(StrictModel):
    slug: str = Field(pattern=r"^a1-0(0[1-9]|10)$")
    title: str = Field(min_length=5, max_length=200)
    introduction: str = Field(min_length=30)
    estimated_minutes: int = Field(ge=10, le=20)
    objectives: list[ObjectiveInput] = Field(min_length=1)
    vocabulary: list[VocabularyInput] = Field(min_length=8, max_length=15)
    examples: list[ExampleInput] = Field(min_length=2)
    grammar: list[GrammarInput] = Field(min_length=1)
    pronunciation: str = Field(min_length=20)
    dialogue: DialogueInput
    exercises: list[ExerciseInput] = Field(min_length=5)
    recap: str = Field(min_length=20)

    @model_validator(mode="after")
    def validate_references(self) -> "LessonInput":
        seen: set[tuple[str, str, str | None]] = set()
        for item in self.vocabulary:
            identity = (
                unicodedata.normalize("NFKC", item.lemma).casefold(),
                item.part_of_speech,
                item.grammatical_gender,
            )
            if identity in seen:
                raise ValueError(f"duplicate normalized vocabulary entry: {item.lemma}")
            seen.add(identity)
        if self.slug[-3:] != f"{int(self.slug[-3:]):03d}":
            raise ValueError("lesson slug must use a stable three-digit position")
        return self


class PlannedCourseInput(StrictModel):
    level: Literal["A2", "B1", "B2", "C1", "C2"]
    slug: str = Field(min_length=3, max_length=120)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20)
    unit_titles: list[str] = Field(min_length=1)


class A1CourseInput(StrictModel):
    slug: str = Field(min_length=3, max_length=120)
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=20)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    units: list[str] = Field(min_length=5, max_length=5)
    lessons: list[LessonInput] = Field(min_length=1, max_length=10)


class ContentImportInput(StrictModel):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    source_name: str = Field(min_length=3, max_length=160)
    source_type: Literal["original_authored", "ai_assisted_draft"]
    source_url: str | None = None
    source_license: str = Field(min_length=8, max_length=160)
    attribution_requirements: str = Field(min_length=8)
    course: A1CourseInput
    planned_courses: list[PlannedCourseInput] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def validate_course_content(self) -> "ContentImportInput":
        if self.course.version != self.version:
            raise ValueError("course version must match the import source version")
        slugs = [lesson.slug for lesson in self.course.lessons]
        if len(slugs) != len(set(slugs)):
            raise ValueError("lesson slugs must be unique")
        positions = [int(slug[-3:]) for slug in slugs]
        if len(positions) != len(set(positions)):
            raise ValueError("lesson positions must be unique")
        if [course.level for course in self.planned_courses] != ["A2", "B1", "B2", "C1", "C2"]:
            raise ValueError("planned courses must cover A2, B1, B2, C1 and C2 exactly once")
        return self


class HumanReviewApproval(StrictModel):
    status: Literal["approved"]
    reviewer: str = Field(min_length=3, max_length=200)
    independent_from_content_generation: bool
    evidence_reference: str = Field(min_length=8, max_length=1000)
    reviewed_at: datetime

    @model_validator(mode="after")
    def require_independent_human_attestation(self) -> "HumanReviewApproval":
        if not self.independent_from_content_generation:
            raise ValueError("reviewer must attest independence from AI content generation")
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("reviewed_at must include a timezone")
        return self


class LessonReviewRecord(StrictModel):
    lesson_slug: str = Field(pattern=r"^a1-0(0[1-9]|10)$")
    french_language: HumanReviewApproval
    pedagogy_and_sequence: HumanReviewApproval
    exercise_answers: HumanReviewApproval


class A1PublicationReviewRecord(StrictModel):
    schema_version: Literal[1]
    course_slug: str = Field(min_length=3, max_length=120)
    content_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    license_and_attribution: HumanReviewApproval
    lessons: list[LessonReviewRecord] = Field(min_length=10, max_length=10)

    @model_validator(mode="after")
    def require_unique_lesson_reviews(self) -> "A1PublicationReviewRecord":
        lesson_slugs = [lesson.lesson_slug for lesson in self.lessons]
        if len(lesson_slugs) != len(set(lesson_slugs)):
            raise ValueError("lesson review slugs must be unique")
        return self
