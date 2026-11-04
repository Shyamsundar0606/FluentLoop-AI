import re
import unicodedata
from uuid import UUID
from sqlalchemy import select
from fastapi import HTTPException
from app.curriculum_models import (
    ExampleSentence,
    LexemeExample,
    LessonVocabulary,
    Lesson,
    Unit,
    Course,
    Pronunciation,
)
from app.api.v1.curriculum import _published_lesson_filter
from app.services.draft_preview import can_preview_drafts
from app.ai.retrieval import source_for
from app.speech.schemas import Target

LIMITATIONS = "Acoustic pronunciation assessment is not available. Recognition matching does not measure phonetic accuracy, and transcript differences cannot identify a particular sound error."


def guidance(db, example_id, lesson_id):
    rows = db.scalars(
        select(Pronunciation)
        .join(LexemeExample, LexemeExample.lexeme_id == Pronunciation.lexeme_id)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == Pronunciation.lexeme_id)
        .where(
            LexemeExample.example_sentence_id == example_id,
            LessonVocabulary.lesson_id == lesson_id,
        )
        .order_by(Pronunciation.id)
        .limit(3)
    ).all()
    notes = " ".join((p.ipa + ": " + (p.pronunciation_notes or ""))[:250] for p in rows)
    return (
        (notes + " " if notes else "")
        + "Listen to the French reference and compare your recording. These are reference notes, not a diagnosis of a sound error."
    )


def targets(db, user, level=None, limit=30):
    rows = db.execute(
        select(ExampleSentence, Lesson)
        .join(LexemeExample, LexemeExample.example_sentence_id == ExampleSentence.id)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == LexemeExample.lexeme_id)
        .join(Lesson, Lesson.id == LessonVocabulary.lesson_id)
        .join(Unit, Unit.id == Lesson.unit_id)
        .join(Course, Course.id == Unit.course_id)
        .where(
            _published_lesson_filter(can_preview_drafts(user)),
            ExampleSentence.cefr_level
            == (level or user.preferences.current_level.upper()),
        )
        .distinct()
        .order_by(Lesson.id, ExampleSentence.id)
        .limit(limit)
    ).all()
    return [
        Target(
            id=f"{example.id}:{lesson.id}",
            text=example.french_text[:500],
            english=example.english_translation[:500],
            level=example.cefr_level,
            lesson_id=lesson.id,
            content_version=lesson.content_version,
            draft_preview=source_for(db, user, lesson.id).draft_preview,
            guidance="Listen to the French reference and compare it with your recording. A recognizer cannot reliably isolate a phoneme mistake.",
        )
        for example, lesson in rows
        if len(example.french_text) <= 500
    ]


def target(db, user, target_id):
    try:
        example_id, lesson_id = [UUID(x) for x in target_id.split(":")]
    except (ValueError, TypeError):
        raise HTTPException(404, "Practice target not found.") from None
    source = source_for(db, user, lesson_id)
    example = db.scalar(
        select(ExampleSentence)
        .join(LexemeExample, LexemeExample.example_sentence_id == ExampleSentence.id)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == LexemeExample.lexeme_id)
        .where(
            ExampleSentence.id == example_id, LessonVocabulary.lesson_id == lesson_id
        )
        .limit(1)
    )
    if not example or len(example.french_text) > 500:
        raise HTTPException(404, "Practice target not found.")
    return Target(
        id=target_id,
        text=example.french_text,
        english=example.english_translation,
        level=example.cefr_level,
        lesson_id=lesson_id,
        content_version=source.content_version,
        draft_preview=source.draft_preview,
        guidance=guidance(db, example_id, lesson_id),
    )


def normalize(text):
    return " ".join(
        re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())
    )


def assess(reference, transcription):
    usable = transcription.status == "transcribed"
    match = normalize(reference) == normalize(transcription.text) if usable else None
    return {
        "recognition_match": match,
        "recognition_feedback": (
            "The recognizer detected the expected words. This is not a pronunciation score."
            if match
            else (
                "The recognized words differ from the target. Compare the texts and listen again; the acoustic cause is unknown."
                if usable
                else "The recording could not be reliably recognized. Try a quiet setting and record again."
            )
        ),
        "assessment_status": "not_available" if usable else "insufficient_audio",
        "limitations": LIMITATIONS,
    }
