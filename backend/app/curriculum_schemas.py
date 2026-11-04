from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LevelResponse(APIModel):
    code: str
    display_name: str
    description: str
    rank: int
    published_course_count: int
    content_available: bool
    draft_preview_course_count: int = 0


class ObjectiveResponse(APIModel):
    code: str
    title: str
    description: str
    skill_category: str


class CourseResponse(APIModel):
    id: UUID
    level: str
    slug: str
    title: str
    description: str
    explanation_language: str
    estimated_minutes: int
    unit_count: int
    lesson_count: int
    objectives: list[ObjectiveResponse]
    content_status: str = "published"
    draft_preview: bool = False


class UnitResponse(APIModel):
    id: UUID
    course_id: UUID
    slug: str
    title: str
    description: str
    sequence_order: int
    lesson_count: int
    content_status: str = "published"
    draft_preview: bool = False


class LessonResponse(APIModel):
    id: UUID
    unit_id: UUID
    slug: str
    title: str
    description: str
    sequence_order: int
    estimated_minutes: int
    level: str
    content_status: str = "published"
    draft_preview: bool = False


class SectionResponse(APIModel):
    type: str
    title: str
    content: str
    sequence_order: int


class DialogueTurnResponse(APIModel):
    speaker_label: str
    sequence_order: int
    french_text: str
    english_translation: str


class DialogueResponse(APIModel):
    id: UUID
    slug: str
    title: str
    level: str
    context: str
    english_context: str
    turns: list[DialogueTurnResponse]


class LessonDetailResponse(LessonResponse):
    sections: list[SectionResponse]
    objectives: list[ObjectiveResponse]
    dialogues: list[DialogueResponse]


class ExampleResponse(APIModel):
    french_text: str
    english_translation: str
    context: str | None


class VocabularyResponse(APIModel):
    id: UUID
    lemma: str
    part_of_speech: str
    grammatical_gender: str | None
    translation: str
    definition_french: str
    ipa: str | None
    examples: list[ExampleResponse]


class GrammarExampleResponse(APIModel):
    french_sentence: str
    english_translation: str
    explanation: str | None


class GrammarResponse(APIModel):
    id: UUID
    slug: str
    title: str
    level: str
    summary: str
    rules: list[str]
    examples: list[GrammarExampleResponse]


class ExerciseOptionResponse(APIModel):
    id: UUID
    text: str
    sequence_order: int


class ExerciseResponse(APIModel):
    id: UUID
    type: str
    prompt: str
    instructions: str
    level: str
    sequence_order: int
    options: list[ExerciseOptionResponse]


class ConjugationResponse(APIModel):
    mood: str
    tense: str
    grammatical_person: int
    grammatical_number: str
    conjugated_form: str
    ipa: str | None


class VerbResponse(APIModel):
    infinitive: str
    verb_group: str
    irregular: bool
    conjugations: list[ConjugationResponse]


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    limit: int
    offset: int
    total: int
