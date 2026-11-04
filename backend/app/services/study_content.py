"""Shared trusted publication/RBAC filters. Never trust a client preview flag."""
import hashlib
import json
from sqlalchemy import select
from app.curriculum_models import Course, Unit, Lesson, LessonVocabulary, Lexeme, WordSense, Translation
from app.services.draft_preview import can_preview_drafts

def lessons(db, user, level):
    query = select(Lesson, Unit, Course).join(Unit, Unit.id == Lesson.unit_id).join(Course, Course.id == Unit.course_id).where(Lesson.difficulty_level == level, Course.level_id == level)
    allowed = ('draft', 'review', 'published') if can_preview_drafts(user) else ('published',)
    query = query.where(Lesson.status.in_(allowed), Unit.status.in_(allowed), Course.status.in_(allowed))
    return [(lesson, not (lesson.status == unit.status == course.status == 'published'))
            for lesson, unit, course in db.execute(query.order_by(Unit.sequence_order, Lesson.sequence_order, Lesson.id))]

def vocabulary(db, user, level):
    permitted = dict((lesson.id, preview) for lesson, preview in lessons(db, user, level))
    if not permitted:
        return {}
    rows = db.execute(select(WordSense, Lexeme, LessonVocabulary.lesson_id)
        .join(Lexeme, WordSense.lexeme_id == Lexeme.id)
        .join(LessonVocabulary, LessonVocabulary.lexeme_id == Lexeme.id)
        .join(Lesson, Lesson.id == LessonVocabulary.lesson_id)
        .join(Unit, Unit.id == Lesson.unit_id)
        .where(LessonVocabulary.lesson_id.in_(permitted))
        .order_by(Unit.sequence_order, Lesson.sequence_order, LessonVocabulary.sequence_order, WordSense.sense_number, WordSense.id)).all()
    result = {}
    for sense, lexeme, lesson_id in rows:
        translations = db.scalars(select(Translation.translated_text).where(
            Translation.word_sense_id == sense.id, Translation.language_code == 'en').order_by(Translation.translated_text)).all()
        meaning = translations[0] if translations else sense.explanation_english
        if not meaning.strip() or not lexeme.lemma.strip():
            continue
        # Start from the canonical stored lemma. Equivalent stored translations
        # are grouped below; no inferred synonyms or new records are invented.
        value = dict(prompt=f'Write in French: {meaning}', answers=[lexeme.lemma],
                     explanation=sense.explanation_english, draft_preview=permitted[lesson_id])
        if sense.id not in result or not permitted[lesson_id]:
            result[sense.id] = value
    equivalents = {}
    equivalent_previews = {}
    for value in result.values():
        equivalents.setdefault(value['prompt'], set()).update(value['answers'])
        equivalent_previews[value['prompt']]=equivalent_previews.get(value['prompt'],False) or value['draft_preview']
    for value in result.values():
        canonical=value['answers'][0]
        value['answers']=[canonical]+sorted(equivalents[value['prompt']]-{canonical})
        value['draft_preview']=equivalent_previews[value['prompt']]
        value['version']=hashlib.sha256(json.dumps({k:v for k,v in value.items() if k!='draft_preview'},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result
