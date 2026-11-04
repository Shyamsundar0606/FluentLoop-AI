"""Read-only A1 reviewer packet audit. Passing does not approve publication."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from app.content_import import load_content, _lemma_for_storage, _norm
from app.curriculum_models import (
    Course, Unit, Lesson, LessonSection, LessonVocabulary, Lexeme, WordSense,
    Translation, Pronunciation, ExampleSentence, LexemeExample, LessonGrammar,
    GrammarTopic, GrammarRule, GrammarExample, LessonDialogue, Dialogue, DialogueTurn,
    Exercise, ExerciseOption, ExerciseAnswer, ContentSource, ImportBatch, ContentProvenance,
    LessonObjective, LearningObjective, VerbLemma, VerbConjugation, Phoneme,
)

ROOT = Path(__file__).resolve().parents[2]


def audit(db, source_path):
    content = load_content(source_path)
    digest = hashlib.sha256(content.model_dump_json().encode()).hexdigest()
    rows = []
    course = db.scalar(select(Course).where(Course.slug == content.course.slug))
    if not course:
        raise ValueError("Current source course is absent from this database")
    units = db.scalars(select(Unit).where(Unit.course_id == course.id).order_by(Unit.sequence_order)).all()
    lessons = db.scalars(select(Lesson).join(Unit).where(Unit.course_id == course.id).order_by(Unit.sequence_order, Lesson.sequence_order)).all()
    for number, expected in enumerate(content.course.lessons):
        issues = []
        checks = []
        def check(label, actual, wanted):
            checks.append(label)
            if actual != wanted:
                issues.append({"check": label, "actual": actual, "expected": wanted})
        lesson = next((row for row in lessons if row.slug == expected.slug), None)
        if not lesson:
            rows.append({"slug": expected.slug, "passed": False, "issues": ["Missing lesson"]})
            continue
        check("lesson metadata", [lesson.title, lesson.description, lesson.estimated_minutes, lesson.content_version, lesson.difficulty_level],
              [expected.title, expected.introduction, expected.estimated_minutes, content.version, "A1"])
        unit = next(row for row in units if row.id == lesson.unit_id)
        check("beginner sequence", [unit.sequence_order, lesson.sequence_order], [number // 2 + 1, number % 2 + 1])
        sections = db.scalars(select(LessonSection).where(LessonSection.lesson_id == lesson.id)).all()
        for kind, body in (("introduction", expected.introduction), ("pronunciation", expected.pronunciation), ("recap", expected.recap)):
            check(f"{kind} section", [s.body_content for s in sections if s.section_type == kind], [body])
        objectives = db.scalars(select(LearningObjective).join(LessonObjective).where(LessonObjective.lesson_id == lesson.id)).all()
        check("objectives", sorted((r.code, r.title, r.description) for r in objectives), sorted((r.code, r.title, r.description) for r in expected.objectives))
        lexemes = db.scalars(select(Lexeme).join(LessonVocabulary).where(LessonVocabulary.lesson_id == lesson.id).order_by(LessonVocabulary.sequence_order)).all()
        check("vocabulary count", len(lexemes), len(expected.vocabulary))
        for word, lexeme in zip(expected.vocabulary, lexemes):
            check(f"lexeme:{word.lemma}", [lexeme.lemma, lexeme.part_of_speech, lexeme.grammatical_gender], [_lemma_for_storage(word.lemma, word.part_of_speech), word.part_of_speech, word.grammatical_gender])
            sense = db.scalar(select(WordSense).where(WordSense.lexeme_id == lexeme.id, WordSense.sense_number == 1))
            check(f"definition:{word.lemma}", [sense.definition_french, sense.explanation_english] if sense else None, [word.definition_french, word.translation])
            translations = db.scalars(select(Translation.translated_text).where(Translation.word_sense_id == sense.id, Translation.language_code == "en")).all() if sense else []
            check(f"translation:{word.lemma}", word.translation in translations, True)
            if word.ipa:
                check(f"IPA:{word.lemma}", word.ipa in db.scalars(select(Pronunciation.ipa).where(Pronunciation.lexeme_id == lexeme.id)).all(), True)
        examples = db.execute(select(ExampleSentence.french_text, ExampleSentence.english_translation).join(LexemeExample).join(LessonVocabulary, LessonVocabulary.lexeme_id == LexemeExample.lexeme_id).where(LessonVocabulary.lesson_id == lesson.id).distinct()).all()
        for example in expected.examples:
            check(f"example:{example.french_text}", (example.french_text, example.english_translation) in examples, True)
        grammar = db.scalars(select(GrammarTopic).join(LessonGrammar).where(LessonGrammar.lesson_id == lesson.id)).all()
        check("grammar topic count", len(grammar), len(expected.grammar))
        for topic in expected.grammar:
            actual = next((g for g in grammar if g.slug == topic.slug), None)
            check(f"grammar:{topic.slug}", [actual.title, actual.summary] if actual else None, [topic.title, topic.summary])
            rule = db.scalar(select(GrammarRule).where(GrammarRule.topic_id == actual.id, GrammarRule.rule_code == topic.rule_code)) if actual else None
            check(f"rule:{topic.rule_code}", rule.explanation_english if rule else None, topic.explanation_english)
            found = db.execute(select(GrammarExample.french_sentence, GrammarExample.english_translation).where(GrammarExample.rule_id == rule.id)).all() if rule else []
            check(f"grammar examples:{topic.rule_code}", sorted(tuple(r) for r in found), sorted(topic.examples))
        dialogues = db.scalars(select(Dialogue).join(LessonDialogue).where(LessonDialogue.lesson_id == lesson.id)).all()
        check("dialogue count", len(dialogues), 1)
        turns = db.scalars(select(DialogueTurn).where(DialogueTurn.dialogue_id == dialogues[0].id).order_by(DialogueTurn.sequence_order)).all() if dialogues else []
        check("dialogue turns and translations", [(t.speaker_label, t.french_text, t.english_translation) for t in turns], [(t.speaker_label, t.french_text, t.english_translation) for t in expected.dialogue.turns])
        exercises = db.scalars(select(Exercise).where(Exercise.lesson_id == lesson.id).order_by(Exercise.sequence_order)).all()
        check("exercise count", len(exercises), len(expected.exercises))
        keys = []
        for index, (exercise, item) in enumerate(zip(exercises, expected.exercises), 1):
            check(f"exercise:{index}", [exercise.prompt, exercise.instructions, exercise.explanation, exercise.exercise_type], [item.prompt, item.instructions, item.explanation, item.exercise_type])
            options = db.scalars(select(ExerciseOption).where(ExerciseOption.exercise_id == exercise.id).order_by(ExerciseOption.sequence_order)).all()
            check(f"options:{index}", [(o.option_text, o.is_correct) for o in options], [(v, i == item.correct_option) for i, v in enumerate(item.options)])
            answers = db.scalars(select(ExerciseAnswer).where(ExerciseAnswer.exercise_id == exercise.id)).all()
            check(f"answer:{index}", [(a.accepted_answer, a.normalized_answer, a.explanation) for a in answers], [(item.options[item.correct_option], _norm(item.options[item.correct_option]), item.explanation)])
            keys.append({"exercise": index, "correct_option_zero_based": item.correct_option, "integrity_checked": True})
        provenance = db.scalar(select(ContentProvenance).where(ContentProvenance.item_type == "lesson", ContentProvenance.item_key == expected.slug, ContentProvenance.content_version == content.version))
        check("lesson provenance", provenance.validation_status if provenance else None, "passed")
        rows.append({"slug": expected.slug, "title": lesson.title, "status": lesson.status, "version": lesson.content_version,
            "automated_checks": len(checks), "passed": not issues, "issues": issues,
            "vocabulary": len(lexemes), "exercises": len(exercises), "dialogue_turns": len(turns), "answer_keys": keys,
            "review_state": provenance.review_state if provenance else None,
            "independent_human_review": bool(provenance and provenance.review_metadata.get("independent_human_review"))})
    source = db.scalar(select(ContentSource).where(ContentSource.source_name == content.source_name))
    batch = db.scalar(select(ImportBatch).where(ImportBatch.content_version == content.version, ImportBatch.source_id == source.id).order_by(ImportBatch.created_at.desc())) if source else None
    return {"source_version": content.version, "source_file_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "publication_source_sha256": digest, "importer_sha256": hashlib.sha256((ROOT / "backend/app/content_import.py").read_bytes()).hexdigest(),
        "source_license": source.source_license if source else None, "attribution": source.attribution_requirements if source else None,
        "source_type": source.source_type if source else None, "source_url": source.source_url if source else None,
        "import_digest_matches": bool(batch and batch.report.get("_source_sha256") == digest),
        "course_status": course.status, "unit_statuses": dict(Counter(u.status for u in units)),
        "lesson_count": len(lessons), "published_lessons": sum(l.status == "published" for l in lessons),
        "lessons": rows, "technical_integrity_passed": len(rows) == 10 and all(r["passed"] for r in rows),
        "reference_verbs": [{"infinitive": v.infinitive, "forms": [r.conjugated_form for r in db.scalars(select(VerbConjugation).where(VerbConjugation.verb_id == v.id).order_by(VerbConjugation.grammatical_number.desc(), VerbConjugation.grammatical_person)).all()]} for v in db.scalars(select(VerbLemma)).all()],
        "phoneme_references": [{"symbol": p.ipa_symbol} for p in db.scalars(select(Phoneme)).all()],
        "publication_approved": False, "review_type": "automated_integrity_only; independent human review and rights approval pending"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as db:
        if engine.dialect.name == "postgresql":
            db.execute(text("SET TRANSACTION READ ONLY"))
        result = audit(db, ROOT / "backend/content/a1/course.json")
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"technical_integrity_passed": result["technical_integrity_passed"], "draft_lessons": result["lesson_count"] - result["published_lessons"], "publication_approved": False}))
