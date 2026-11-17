"""Bounded staff edits to resources exclusively linked to one unpublished course."""
from fastapi import HTTPException
from sqlalchemy import select

from app.curriculum_models import (
    ExampleSentence, Exercise, GrammarExample, GrammarRule, GrammarTopic, LearningObjective,
    LessonGrammar, LessonObjective, LessonVocabulary, Lexeme, LexemeExample,
    Translation, VerbConjugation, VerbLemma, WordSense,
)

RESOURCES = {
    "objective": (LearningObjective, ("title", "description")),
    "grammar_topic": (GrammarTopic, ("title", "summary")),
    "grammar_rule": (GrammarRule, ("explanation_english", "explanation_french", "exceptions")),
    "grammar_example": (GrammarExample, ("french_sentence", "english_translation", "explanation")),
    "word_sense": (WordSense, ("definition_french", "explanation_english", "usage_notes")),
    "translation": (Translation, ("translated_text", "context_note")),
    "example": (ExampleSentence, ("french_text", "english_translation", "context")),
    "conjugation": (VerbConjugation, ("conjugated_form", "ipa")),
}


def linked_lessons(db, kind, row):
    if kind == "objective":
        return set(db.scalars(select(LessonObjective.lesson_id).where(LessonObjective.objective_id == row.id))) | set(
            db.scalars(select(Exercise.lesson_id).where(Exercise.learning_objective_id == row.id)))
    if kind in ("grammar_topic", "grammar_rule", "grammar_example"):
        topic = row if kind == "grammar_topic" else db.get(GrammarTopic,
            row.topic_id if kind == "grammar_rule" else db.get(GrammarRule, row.rule_id).topic_id)
        if topic.publication_status not in ("draft", "review", "inherited"):
            raise HTTPException(409, "Published or retired grammar requires a separately reviewed release.")
        return set(db.scalars(select(LessonGrammar.lesson_id).where(LessonGrammar.grammar_topic_id == topic.id))) | set(
            db.scalars(select(Exercise.lesson_id).where(Exercise.grammar_topic_id == topic.id)))
    if kind == "word_sense":
        lexical_ids = [row.lexeme_id]
    elif kind == "translation":
        lexical_ids = [db.get(WordSense, row.word_sense_id).lexeme_id]
    elif kind == "example":
        lexical_ids = db.scalars(select(LexemeExample.lexeme_id).where(LexemeExample.example_sentence_id == row.id)).all()
    else:
        verb = db.get(VerbLemma, row.verb_id)
        lexical_ids = db.scalars(select(Lexeme.id).where(Lexeme.normalized_lemma == verb.normalized_infinitive)).all()
    return set(db.scalars(select(LessonVocabulary.lesson_id).where(LessonVocabulary.lexeme_id.in_(lexical_ids))))


def resource_packet(db, lesson_ids):
    objective_ids = select(LessonObjective.objective_id).where(LessonObjective.lesson_id.in_(lesson_ids))
    topic_ids = select(LessonGrammar.grammar_topic_id).where(LessonGrammar.lesson_id.in_(lesson_ids))
    rule_ids = select(GrammarRule.id).where(GrammarRule.topic_id.in_(topic_ids))
    lexeme_ids = select(LessonVocabulary.lexeme_id).where(LessonVocabulary.lesson_id.in_(lesson_ids))
    sense_ids = select(WordSense.id).where(WordSense.lexeme_id.in_(lexeme_ids))
    queries = {
        "objective": select(LearningObjective).where(LearningObjective.id.in_(objective_ids)),
        "grammar_topic": select(GrammarTopic).where(GrammarTopic.id.in_(topic_ids)),
        "grammar_rule": select(GrammarRule).where(GrammarRule.id.in_(rule_ids)),
        "grammar_example": select(GrammarExample).where(GrammarExample.rule_id.in_(rule_ids)),
        "word_sense": select(WordSense).where(WordSense.id.in_(sense_ids)),
        "translation": select(Translation).where(Translation.word_sense_id.in_(sense_ids)),
        "example": select(ExampleSentence).where(ExampleSentence.id.in_(select(LexemeExample.example_sentence_id)
            .where(LexemeExample.lexeme_id.in_(lexeme_ids)))),
        "conjugation": select(VerbConjugation).join(VerbLemma).where(VerbLemma.normalized_infinitive.in_(
            select(Lexeme.normalized_lemma).where(Lexeme.id.in_(lexeme_ids)))),
    }
    result = []
    for kind, query in queries.items():
        model, fields = RESOURCES[kind]
        for row in db.scalars(query.order_by(model.id)):
            try:
                linked = linked_lessons(db, kind, row)
                editable = bool(linked) and linked <= set(lesson_ids)
            except HTTPException:
                editable = False
            result.append(dict(kind=kind, id=str(row.id), editable=editable,
                values={field: getattr(row, field) for field in fields}))
    return result


def edit_resource(db, lesson_ids, payload):
    entry = RESOURCES.get(payload.kind)
    if entry is None:
        raise HTTPException(422, "Unsupported curriculum resource.")
    model, fields = entry
    row = db.scalar(select(model).where(model.id == payload.resource_id).with_for_update())
    if row is None:
        raise HTTPException(404, "Curriculum resource unavailable.")
    linked = linked_lessons(db, payload.kind, row)
    if not linked.intersection(lesson_ids):
        raise HTTPException(404, "Curriculum resource unavailable for this course.")
    if not linked <= set(lesson_ids):
        raise HTTPException(409, "This resource is shared with another course. Author a separate versioned resource instead.")
    if not payload.values or not set(payload.values) <= set(fields):
        raise HTTPException(422, "Only the listed resource text fields can be edited.")
    for field, value in payload.values.items():
        column = model.__table__.columns[field]
        bound = getattr(column.type, "length", None) or 4000
        if value is None:
            if not column.nullable:
                raise HTTPException(422, "Required resource text cannot be null.")
        elif not value.strip() or len(value) > bound:
            raise HTTPException(422, "Resource text must be nonempty and within the field limit.")
        setattr(row, field, value)
