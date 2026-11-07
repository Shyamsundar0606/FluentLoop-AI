"""Bounded SQL retrieval; lessons are the trusted source/authorization unit.

Never query exercises, exercise options, accepted answers, session snapshots or
arbitrary provenance text for model context.
"""

import re
import unicodedata
from sqlalchemy import select, or_, func
from app.curriculum_models import (
    Course,
    Unit,
    Lesson,
    LessonSection,
    LessonVocabulary,
    Lexeme,
    WordSense,
    LessonGrammar,
    GrammarTopic,
    GrammarRule,
    GrammarExample,
    LessonDialogue,
    Dialogue,
    DialogueTurn,
    LessonObjective,
    LearningObjective,
    LexemeExample,
    ExampleSentence,
    VerbLemma,
    VerbConjugation,
)
from app.services.draft_preview import can_preview_drafts
from app.api.v1.curriculum import _published_lesson_filter, _require_published_lesson
from app.ai.response_schemas import Source


def normalize(text):
    return unicodedata.normalize("NFKC", text).casefold()


def terms(question):
    stop = {
        "what",
        "does",
        "mean",
        "the",
        "and",
        "explain",
        "difference",
        "between",
        "why",
        "how",
        "french",
        "with",
        "that",
        "this",
        "instead",
        "use",
    }
    return list(
        dict.fromkeys(
            t
            for t in re.findall(r"[^\W\d_]+", normalize(question))
            if len(t) > 1 and t not in stop
        )
    )[:8]


def source_for(db, user, lesson_id):
    lesson = _require_published_lesson(
        db, lesson_id, include_preview=can_preview_drafts(user)
    )
    unit = db.get(Unit, lesson.unit_id)
    course = db.get(Course, unit.course_id)
    return Source(
        lesson_id=lesson.id,
        source_record_id=lesson.id,
        title=lesson.title,
        content_version=lesson.content_version,
        draft_preview=any(x.status != "published" for x in (lesson, unit, course)),
        url=f"/lessons/{lesson.id}",
    )


def retrieve(db, user, level, question, linked_lesson_id=None):
    tokens = terms(question)
    conditions = []
    for token in tokens:

        def match(column):
            return func.lower(column).contains(token, autoescape=True)

        conditions.extend(
            [
                match(Lesson.title),
                match(Lesson.description),
                match(Course.title),
                match(Course.description),
                Lesson.id.in_(
                    select(LessonSection.lesson_id).where(
                        match(LessonSection.body_content) | match(LessonSection.title)
                    )
                ),
                Lesson.id.in_(
                    select(LessonVocabulary.lesson_id)
                    .join(Lexeme, Lexeme.id == LessonVocabulary.lexeme_id)
                    .where(match(Lexeme.normalized_lemma))
                ),
                Lesson.id.in_(
                    select(LessonGrammar.lesson_id)
                    .join(
                        GrammarTopic, GrammarTopic.id == LessonGrammar.grammar_topic_id
                    )
                    .where(match(GrammarTopic.title) | match(GrammarTopic.summary))
                    .where(GrammarTopic.publication_status.in_(['inherited','published','draft','review'] if can_preview_drafts(user) else ['inherited','published']))
                ),
                Lesson.id.in_(
                    select(LessonDialogue.lesson_id)
                    .join(Dialogue, Dialogue.id == LessonDialogue.dialogue_id)
                    .where(match(Dialogue.title) | match(Dialogue.context))
                ),
                Lesson.id.in_(
                    select(LessonObjective.lesson_id)
                    .join(
                        LearningObjective,
                        LearningObjective.id == LessonObjective.objective_id,
                    )
                    .where(
                        match(LearningObjective.title)
                        | match(LearningObjective.description)
                    )
                ),
            ]
        )
    if linked_lesson_id:
        source_for(db, user, linked_lesson_id)
        conditions.append(Lesson.id == linked_lesson_id)
    if not conditions:
        return []
    candidates = db.scalars(
        select(Lesson)
        .join(Unit, Lesson.unit_id == Unit.id)
        .join(Course, Unit.course_id == Course.id)
        .where(
            _published_lesson_filter(can_preview_drafts(user)),
            Course.level_id == level,
            or_(*conditions),
        )
        .order_by(Lesson.slug, Lesson.id)
        .limit(24)
    ).all()
    ranked = []
    for lesson in candidates:
        text = (lesson.title + " " + lesson.description)[:1500]
        sections = db.scalars(
            select(LessonSection)
            .where(LessonSection.lesson_id == lesson.id)
            .order_by(LessonSection.sequence_order)
            .limit(5)
        ).all()
        # Practice sections can embed answers: only narrative explanation sections.
        text += "\n" + "\n".join(
            s.body_content[:600]
            for s in sections
            if s.section_type
            in {"introduction", "explanation", "summary", "grammar", "vocabulary"}
        )
        words = db.scalars(
            select(Lexeme)
            .join(LessonVocabulary, LessonVocabulary.lexeme_id == Lexeme.id)
            .where(LessonVocabulary.lesson_id == lesson.id)
            .order_by(Lexeme.normalized_lemma)
            .limit(12)
        ).all()
        for word in words:
            if tokens and not any(
                t in normalize(word.lemma) or normalize(word.lemma) in t for t in tokens
            ):
                continue
            senses = db.scalars(
                select(WordSense)
                .where(WordSense.lexeme_id == word.id)
                .order_by(WordSense.sense_number)
                .limit(2)
            ).all()
            text += (
                "\n"
                + word.lemma
                + " ("
                + word.part_of_speech
                + "): "
                + "; ".join(s.explanation_english[:200] for s in senses)
            )
            examples = db.scalars(
                select(ExampleSentence)
                .join(
                    LexemeExample,
                    LexemeExample.example_sentence_id == ExampleSentence.id,
                )
                .where(
                    LexemeExample.lexeme_id == word.id,
                    ExampleSentence.cefr_level == level,
                )
                .order_by(ExampleSentence.id)
                .limit(2)
            ).all()
            text += " ".join(
                e.french_text[:150] + " = " + e.english_translation[:150]
                for e in examples
            )
            verb = db.scalar(
                select(VerbLemma).where(
                    VerbLemma.normalized_infinitive == word.normalized_lemma
                )
            )
            if verb:
                forms = db.scalars(
                    select(VerbConjugation)
                    .where(VerbConjugation.verb_id == verb.id)
                    .order_by(VerbConjugation.tense, VerbConjugation.grammatical_person)
                    .limit(6)
                ).all()
                text += "\nConjugations: " + "; ".join(
                    f.tense + " " + f.conjugated_form for f in forms
                )
        topics = db.scalars(
            select(GrammarTopic)
            .join(LessonGrammar, LessonGrammar.grammar_topic_id == GrammarTopic.id)
            .where(LessonGrammar.lesson_id == lesson.id,
                GrammarTopic.publication_status.in_(('inherited','published','draft','review') if can_preview_drafts(user) else ('inherited','published')))
            .order_by(GrammarTopic.slug)
            .limit(4)
        ).all()
        for topic in topics:
            text += "\n" + topic.title + ": " + topic.summary[:300]
            rules = db.scalars(
                select(GrammarRule)
                .where(GrammarRule.topic_id == topic.id)
                .order_by(GrammarRule.rule_code)
                .limit(3)
            ).all()
            for rule in rules:
                text += (
                    "\n"
                    + rule.explanation_english[:350]
                    + " "
                    + (rule.exceptions or "")[:150]
                )
                examples = db.scalars(
                    select(GrammarExample)
                    .where(GrammarExample.rule_id == rule.id)
                    .order_by(GrammarExample.id)
                    .limit(2)
                ).all()
                text += " ".join(
                    e.french_sentence[:150] + " = " + e.english_translation[:150]
                    for e in examples
                )
        dialogues = db.scalars(
            select(Dialogue)
            .join(LessonDialogue, LessonDialogue.dialogue_id == Dialogue.id)
            .where(LessonDialogue.lesson_id == lesson.id)
            .order_by(Dialogue.slug)
            .limit(1)
        ).all()
        for dialogue in dialogues:
            turns = db.scalars(
                select(DialogueTurn)
                .where(DialogueTurn.dialogue_id == dialogue.id)
                .order_by(DialogueTurn.sequence_order)
                .limit(4)
            ).all()
            text += (
                "\n"
                + dialogue.title
                + ": "
                + " ".join(t.french_text[:150] for t in turns)
            )
        objectives = db.scalars(
            select(LearningObjective)
            .join(LessonObjective, LessonObjective.objective_id == LearningObjective.id)
            .where(LessonObjective.lesson_id == lesson.id)
            .order_by(LearningObjective.code)
            .limit(3)
        ).all()
        text += "\nObjectives: " + "; ".join(o.title[:150] for o in objectives)
        score = sum(normalize(text).count(t) for t in tokens) + (
            100 if lesson.id == linked_lesson_id else 0
        )
        ranked.append(
            {
                "source": source_for(db, user, lesson.id).model_dump(mode="json"),
                "text": text[:2400],
                "score": score,
            }
        )
    return sorted(ranked, key=lambda x: (-x["score"], str(x["source"]["lesson_id"])))[
        :3
    ]
