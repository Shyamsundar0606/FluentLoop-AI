from __future__ import annotations

import unicodedata
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.curriculum_models import (
    CefrLevel,
    Course,
    Dialogue,
    DialogueTurn,
    ExampleSentence,
    Exercise,
    ExerciseOption,
    GrammarExample,
    GrammarRule,
    GrammarTopic,
    Lesson,
    LessonDialogue,
    LessonGrammar,
    LessonObjective,
    LessonSection,
    LessonVocabulary,
    LearningObjective,
    Lexeme,
    LexemeExample,
    Pronunciation,
    Translation,
    Unit,
    VerbConjugation,
    VerbLemma,
    WordSense,
)
from app.dependencies import AuthContext, current_auth_context
from app.services.draft_preview import can_preview_drafts
from app.curriculum_schemas import (
    CourseResponse,
    DialogueResponse,
    ExerciseResponse,
    GrammarResponse,
    LessonDetailResponse,
    LessonResponse,
    LevelResponse,
    PaginatedResponse,
    UnitResponse,
    VerbResponse,
    VocabularyResponse,
)

router = APIRouter(tags=["curriculum"])
CEFR = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


def _level(context: AuthContext, requested: str | None) -> str:
    return requested or context.user.preferences.current_level.upper()


def _published_course_filter(include_preview: bool = False):
    if include_preview:
        return Course.status.in_(("published", "draft", "review"))
    return Course.status == "published"


def _published_lesson_filter(include_preview: bool = False):
    statuses = ("published", "draft", "review") if include_preview else ("published",)
    return (
        Lesson.status.in_(statuses)
        & Unit.status.in_(statuses)
        & Course.status.in_(statuses)
    )


def _require_published_lesson(
    db: Session,
    lesson_id: UUID,
    *,
    include_preview: bool = False,
) -> Lesson:
    lesson = db.scalar(
        select(Lesson)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(Lesson.id == lesson_id, _published_lesson_filter(include_preview))
    )
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    return lesson


def _course_response(db: Session, course: Course, *, include_preview: bool = False) -> dict:
    statuses = ("published", "draft", "review") if include_preview else ("published",)
    unit_count = db.scalar(
        select(func.count(Unit.id)).where(Unit.course_id == course.id, Unit.status.in_(statuses))
    ) or 0
    lesson_count = db.scalar(
        select(func.count(Lesson.id))
        .join(Unit, Lesson.unit_id == Unit.id)
        .where(Unit.course_id == course.id, Unit.status.in_(statuses), Lesson.status.in_(statuses))
    ) or 0
    objectives = db.scalars(
        select(LearningObjective)
        .join(LessonObjective, LearningObjective.id == LessonObjective.objective_id)
        .join(Lesson, LessonObjective.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .where(
            Unit.course_id == course.id,
            Unit.status.in_(statuses),
            Lesson.status.in_(statuses),
        )
        .distinct()
        .order_by(LearningObjective.code)
    ).all()
    return {
        "id": course.id,
        "level": course.level_id,
        "slug": course.slug,
        "title": course.title,
        "description": course.description,
        "explanation_language": course.explanation_language,
        "estimated_minutes": course.estimated_minutes,
        "content_status": course.status,
        "draft_preview": course.status != "published",
        "unit_count": unit_count,
        "lesson_count": lesson_count,
        "objectives": [
            {
                "code": item.code,
                "title": item.title,
                "description": item.description,
                "skill_category": item.skill_category,
            }
            for item in objectives
        ],
    }


def _vocabulary_items(
    db: Session,
    *,
    level: str,
    limit: int,
    offset: int,
    search: str | None = None,
    lesson_id: UUID | None = None,
    include_preview: bool = False,
) -> tuple[list[dict], int]:
    eligible_lessons = (
        select(LessonVocabulary.lexeme_id)
        .join(Lesson, LessonVocabulary.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(_published_lesson_filter(include_preview), Course.level_id == level)
    )
    if lesson_id is not None:
        eligible_lessons = eligible_lessons.where(Lesson.id == lesson_id)
    ids = select(Lexeme.id).where(Lexeme.id.in_(eligible_lessons))
    if search:
        normalized_search = unicodedata.normalize("NFKC", search).casefold()
        ids = ids.where(Lexeme.normalized_lemma.contains(normalized_search, autoescape=True))
    id_query = ids.distinct()
    total = db.scalar(select(func.count()).select_from(id_query.subquery())) or 0
    rows = db.scalars(
        select(Lexeme)
        .where(Lexeme.id.in_(id_query))
        .order_by(Lexeme.normalized_lemma, Lexeme.part_of_speech, Lexeme.grammatical_gender)
        .offset(offset)
        .limit(limit)
    ).all()
    items: list[dict] = []
    for lexeme in rows:
        sense = db.scalar(select(WordSense).where(WordSense.lexeme_id == lexeme.id).order_by(WordSense.sense_number))
        if sense is None:
            continue
        translation = db.scalar(
            select(Translation.translated_text)
            .where(Translation.word_sense_id == sense.id, Translation.language_code == "en")
            .order_by(Translation.translated_text)
        )
        pronunciations = db.scalars(
            select(Pronunciation).where(Pronunciation.lexeme_id == lexeme.id).order_by(Pronunciation.accent_variant)
        ).all()
        examples = db.scalars(
            select(ExampleSentence)
            .join(LexemeExample, ExampleSentence.id == LexemeExample.example_sentence_id)
            .where(LexemeExample.lexeme_id == lexeme.id, ExampleSentence.cefr_level == level)
            .order_by(ExampleSentence.french_text)
            .limit(5)
        ).all()
        items.append(
            {
                "id": lexeme.id,
                "lemma": lexeme.lemma,
                "part_of_speech": lexeme.part_of_speech,
                "grammatical_gender": lexeme.grammatical_gender,
                "translation": translation or sense.explanation_english,
                "definition_french": sense.definition_french,
                "ipa": pronunciations[0].ipa if pronunciations else None,
                "examples": [
                    {
                        "french_text": item.french_text,
                        "english_translation": item.english_translation,
                        "context": item.context,
                    }
                    for item in examples
                ],
            }
        )
    return items, total


def _grammar_items(
    db: Session,
    *,
    level: str,
    limit: int,
    offset: int,
    lesson_id: UUID | None = None,
    include_preview: bool = False,
) -> tuple[list[dict], int]:
    topic_ids = (
        select(LessonGrammar.grammar_topic_id)
        .join(Lesson, LessonGrammar.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(_published_lesson_filter(include_preview), Course.level_id == level)
    )
    if lesson_id is not None:
        topic_ids = topic_ids.where(Lesson.id == lesson_id)
    total = db.scalar(
        select(func.count(GrammarTopic.id)).where(
            GrammarTopic.id.in_(topic_ids), GrammarTopic.cefr_level == level,
            GrammarTopic.publication_status.in_(('inherited','published','draft','review') if include_preview else ('inherited','published')),
        )
    ) or 0
    topics = db.scalars(
        select(GrammarTopic)
        .where(GrammarTopic.id.in_(topic_ids), GrammarTopic.cefr_level == level,
            GrammarTopic.publication_status.in_(('inherited','published','draft','review') if include_preview else ('inherited','published')))
        .order_by(GrammarTopic.title, GrammarTopic.slug)
        .offset(offset)
        .limit(limit)
    ).all()
    items: list[dict] = []
    for topic in topics:
        rules = db.scalars(select(GrammarRule).where(GrammarRule.topic_id == topic.id).order_by(GrammarRule.rule_code)).all()
        examples = []
        for rule in rules:
            examples.extend(
                db.scalars(
                    select(GrammarExample)
                    .where(GrammarExample.rule_id == rule.id)
                    .order_by(GrammarExample.french_sentence)
                    .limit(10)
                ).all()
            )
        items.append(
            {
                "id": topic.id,
                "slug": topic.slug,
                "title": topic.title,
                "level": topic.cefr_level,
                "summary": topic.summary,
                "rules": [rule.explanation_english for rule in rules],
                "examples": [
                    {
                        "french_sentence": item.french_sentence,
                        "english_translation": item.english_translation,
                        "explanation": item.explanation,
                    }
                    for item in examples
                ],
            }
        )
    return items, total


@router.get("/levels", response_model=list[LevelResponse])
def list_levels(
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    include_preview = can_preview_drafts(context.user)
    levels = db.scalars(select(CefrLevel).order_by(CefrLevel.rank)).all()
    result = []
    for level in levels:
        published_count = db.scalar(
            select(func.count(Course.id)).where(
                Course.level_id == level.code,
                Course.status == "published",
            )
        ) or 0
        preview_count = 0
        if include_preview:
            preview_count = db.scalar(
                select(func.count(Course.id)).where(
                    Course.level_id == level.code,
                    Course.status.in_(("draft", "review")),
                )
            ) or 0
        result.append(
            {
                "code": level.code,
                "display_name": level.display_name,
                "description": level.description,
                "rank": level.rank,
                "published_course_count": published_count,
                "content_available": published_count > 0 or preview_count > 0,
                "draft_preview_course_count": preview_count,
            }
        )
    return result


@router.get("/courses", response_model=PaginatedResponse[CourseResponse])
def list_courses(
    level: CEFR | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    selected_level = _level(context, level)
    include_preview = can_preview_drafts(context.user)
    query = select(Course).where(
        Course.level_id == selected_level,
        _published_course_filter(include_preview),
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    courses = db.scalars(query.order_by(Course.slug).offset(offset).limit(limit)).all()
    return {
        "items": [
            _course_response(db, course, include_preview=include_preview)
            for course in courses
        ],
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get("/courses/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    include_preview = can_preview_drafts(context.user)
    course = db.scalar(
        select(Course).where(
            Course.id == course_id,
            _published_course_filter(include_preview),
        )
    )
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    return _course_response(db, course, include_preview=include_preview)


@router.get("/courses/{course_id}/units", response_model=PaginatedResponse[UnitResponse])
def list_course_units(
    course_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    include_preview = can_preview_drafts(context.user)
    course = db.scalar(
        select(Course).where(
            Course.id == course_id,
            _published_course_filter(include_preview),
        )
    )
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found.")
    statuses = ("published", "draft", "review") if include_preview else ("published",)
    query = select(Unit).where(Unit.course_id == course_id, Unit.status.in_(statuses))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    units = db.scalars(query.order_by(Unit.sequence_order).offset(offset).limit(limit)).all()
    return {
        "items": [
            {
                "id": unit.id,
                "course_id": unit.course_id,
                "slug": unit.slug,
                "title": unit.title,
                "description": unit.description,
                "sequence_order": unit.sequence_order,
                "lesson_count": db.scalar(
                    select(func.count(Lesson.id)).where(
                        Lesson.unit_id == unit.id, Lesson.status.in_(statuses)
                    )
                ) or 0,
                "content_status": unit.status,
                "draft_preview": unit.status != "published",
            }
            for unit in units
        ],
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get("/units/{unit_id}/lessons", response_model=PaginatedResponse[LessonResponse])
def list_unit_lessons(
    unit_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    include_preview = can_preview_drafts(context.user)
    statuses = ("published", "draft", "review") if include_preview else ("published",)
    unit = db.scalar(
        select(Unit)
        .join(Course, Unit.course_id == Course.id)
        .where(
            Unit.id == unit_id,
            Unit.status.in_(statuses),
            Course.status.in_(statuses),
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found.")
    query = select(Lesson).where(Lesson.unit_id == unit_id, Lesson.status.in_(statuses))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    lessons = db.scalars(query.order_by(Lesson.sequence_order).offset(offset).limit(limit)).all()
    return {
        "items": [
            {
                "id": item.id,
                "unit_id": item.unit_id,
                "slug": item.slug,
                "title": item.title,
                "description": item.description,
                "sequence_order": item.sequence_order,
                "estimated_minutes": item.estimated_minutes,
                "level": item.difficulty_level,
                "content_status": item.status,
                "draft_preview": item.status != "published",
            }
            for item in lessons
        ],
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
def get_lesson(
    lesson_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    lesson = _require_published_lesson(
        db,
        lesson_id,
        include_preview=can_preview_drafts(context.user),
    )
    sections = db.scalars(
        select(LessonSection).where(LessonSection.lesson_id == lesson.id).order_by(LessonSection.sequence_order)
    ).all()
    objectives = db.scalars(
        select(LearningObjective)
        .join(LessonObjective, LearningObjective.id == LessonObjective.objective_id)
        .where(LessonObjective.lesson_id == lesson.id)
        .order_by(LearningObjective.code)
    ).all()
    dialogues = db.scalars(
        select(Dialogue)
        .join(LessonDialogue, LessonDialogue.dialogue_id == Dialogue.id)
        .where(LessonDialogue.lesson_id == lesson.id)
        .order_by(Dialogue.slug)
    ).all()
    return {
        "id": lesson.id,
        "unit_id": lesson.unit_id,
        "slug": lesson.slug,
        "title": lesson.title,
        "description": lesson.description,
        "sequence_order": lesson.sequence_order,
        "estimated_minutes": lesson.estimated_minutes,
        "level": lesson.difficulty_level,
        "content_status": lesson.status,
        "draft_preview": lesson.status != "published",
        "sections": [
            {
                "type": section.section_type,
                "title": section.title,
                "content": section.body_content,
                "sequence_order": section.sequence_order,
            }
            for section in sections
        ],
        "objectives": [
            {
                "code": item.code,
                "title": item.title,
                "description": item.description,
                "skill_category": item.skill_category,
            }
            for item in objectives
        ],
        "dialogues": [
            {
                "id": dialogue.id,
                "slug": dialogue.slug,
                "title": dialogue.title,
                "level": dialogue.cefr_level,
                "context": dialogue.context,
                "english_context": dialogue.english_context,
                "turns": [
                    {
                        "speaker_label": turn.speaker_label,
                        "sequence_order": turn.sequence_order,
                        "french_text": turn.french_text,
                        "english_translation": turn.english_translation,
                    }
                    for turn in db.scalars(
                        select(DialogueTurn)
                        .where(DialogueTurn.dialogue_id == dialogue.id)
                        .order_by(DialogueTurn.sequence_order)
                    ).all()
                ],
            }
            for dialogue in dialogues
        ],
    }


@router.get("/lessons/{lesson_id}/vocabulary", response_model=PaginatedResponse[VocabularyResponse])
def list_lesson_vocabulary(
    lesson_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    include_preview = can_preview_drafts(context.user)
    lesson = _require_published_lesson(db, lesson_id, include_preview=include_preview)
    items, total = _vocabulary_items(
        db,
        level=lesson.difficulty_level,
        limit=limit,
        offset=offset,
        lesson_id=lesson.id,
        include_preview=include_preview,
    )
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@router.get("/lessons/{lesson_id}/grammar", response_model=PaginatedResponse[GrammarResponse])
def list_lesson_grammar(
    lesson_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    include_preview = can_preview_drafts(context.user)
    lesson = _require_published_lesson(db, lesson_id, include_preview=include_preview)
    items, total = _grammar_items(
        db,
        level=lesson.difficulty_level,
        limit=limit,
        offset=offset,
        lesson_id=lesson.id,
        include_preview=include_preview,
    )
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@router.get("/lessons/{lesson_id}/exercises", response_model=PaginatedResponse[ExerciseResponse])
def list_lesson_exercises(
    lesson_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    lesson = _require_published_lesson(
        db,
        lesson_id,
        include_preview=can_preview_drafts(context.user),
    )
    allowed_topics=select(GrammarTopic.id).where(GrammarTopic.publication_status.in_(
        ('inherited','published','draft','review') if can_preview_drafts(context.user) else ('inherited','published')))
    query = select(Exercise).where(Exercise.lesson_id == lesson.id).where(
        (Exercise.grammar_topic_id.is_(None)) | Exercise.grammar_topic_id.in_(allowed_topics))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    exercises = db.scalars(query.order_by(Exercise.sequence_order).offset(offset).limit(limit)).all()
    return {
        "items": [
            {
                "id": exercise.id,
                "type": exercise.exercise_type,
                "prompt": exercise.prompt,
                "instructions": exercise.instructions,
                "level": exercise.level,
                "sequence_order": exercise.sequence_order,
                "options": [
                    {
                        "id": option.id,
                        "text": option.option_text,
                        "sequence_order": option.sequence_order,
                    }
                    for option in db.scalars(
                        select(ExerciseOption)
                        .where(ExerciseOption.exercise_id == exercise.id)
                        .order_by(ExerciseOption.sequence_order)
                    ).all()
                ],
            }
            for exercise in exercises
        ],
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get("/vocabulary", response_model=PaginatedResponse[VocabularyResponse])
def search_vocabulary(
    level: CEFR | None = None,
    search: str | None = Query(None, min_length=1, max_length=80),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    items, total = _vocabulary_items(
        db,
        level=_level(context, level),
        limit=limit,
        offset=offset,
        search=search,
        include_preview=can_preview_drafts(context.user),
    )
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@router.get("/verbs/{infinitive}/conjugations", response_model=VerbResponse)
def get_verb_conjugations(
    infinitive: str,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    normalized = unicodedata.normalize("NFKC", infinitive).casefold()
    public_lexeme = db.scalar(
        select(Lexeme.id)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == Lexeme.id)
        .join(Lesson, LessonVocabulary.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(
            Lexeme.normalized_lemma == normalized,
            Lexeme.part_of_speech == "verb",
            _published_lesson_filter(can_preview_drafts(context.user)),
        )
    )
    if public_lexeme is None:
        raise HTTPException(status_code=404, detail="Verb reference not found.")
    verb = db.scalar(select(VerbLemma).where(VerbLemma.normalized_infinitive == normalized))
    if verb is None:
        raise HTTPException(status_code=404, detail="Verb reference not found.")
    forms = db.scalars(
        select(VerbConjugation)
        .where(VerbConjugation.verb_id == verb.id)
        .order_by(VerbConjugation.mood, VerbConjugation.tense, VerbConjugation.grammatical_person, VerbConjugation.grammatical_number)
    ).all()
    return {
        "infinitive": verb.infinitive,
        "verb_group": verb.verb_group,
        "irregular": verb.irregular,
        "conjugations": [
            {
                "mood": form.mood,
                "tense": form.tense,
                "grammatical_person": form.grammatical_person,
                "grammatical_number": form.grammatical_number,
                "conjugated_form": form.conjugated_form,
                "ipa": form.ipa,
            }
            for form in forms
        ],
    }


@router.get("/grammar", response_model=PaginatedResponse[GrammarResponse])
def list_grammar(
    level: CEFR | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    items, total = _grammar_items(
        db,
        level=_level(context, level),
        limit=limit,
        offset=offset,
        include_preview=can_preview_drafts(context.user),
    )
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@router.get("/dialogues", response_model=PaginatedResponse[DialogueResponse])
def list_dialogues(
    level: CEFR | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    selected_level = _level(context, level)
    query = (
        select(Dialogue)
        .join(LessonDialogue, LessonDialogue.dialogue_id == Dialogue.id)
        .join(Lesson, LessonDialogue.lesson_id == Lesson.id)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(
            _published_lesson_filter(can_preview_drafts(context.user)),
            Course.level_id == selected_level,
        )
    )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    dialogues = db.scalars(query.order_by(Dialogue.slug).offset(offset).limit(limit)).all()
    return {
        "items": [
            {
                "id": dialogue.id,
                "slug": dialogue.slug,
                "title": dialogue.title,
                "level": dialogue.cefr_level,
                "context": dialogue.context,
                "english_context": dialogue.english_context,
                "turns": [
                    {
                        "speaker_label": turn.speaker_label,
                        "sequence_order": turn.sequence_order,
                        "french_text": turn.french_text,
                        "english_translation": turn.english_translation,
                    }
                    for turn in db.scalars(
                        select(DialogueTurn)
                        .where(DialogueTurn.dialogue_id == dialogue.id)
                        .order_by(DialogueTurn.sequence_order)
                    ).all()
                ],
            }
            for dialogue in dialogues
        ],
        "limit": limit,
        "offset": offset,
        "total": total,
    }
