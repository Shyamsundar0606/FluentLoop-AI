"""Validated, versioned assessment drafts imported through existing content helpers."""
import hashlib
import unicodedata
import re
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select

from app.content_import import _upsert, _provenance
from app.content_schemas import CEFR, VocabularyInput, GrammarInput
from app.curriculum_models import (
    ContentSource, Course, Exercise, ExerciseOption, ImportBatch, LearningObjective,
    Lesson, LessonObjective, LessonSection, LessonVocabulary, Lexeme, Unit,
    WordSense, Translation, GrammarTopic, GrammarRule, GrammarExample, LessonGrammar, LessonPrerequisite,
)
from app.interactive_content import ExerciseInput, Strict

CONTENT_PATH = Path(__file__).resolve().parents[1] / "content/practice/a1-assessments-0.1.0.json"


class AssessmentTask(Strict):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{2,40}$")
    skill: Literal["vocabulary", "grammar", "reading", "writing"]
    title: str = Field(min_length=5, max_length=160)
    objective: str = Field(min_length=10, max_length=500)
    context: str = Field(min_length=20, max_length=2000)
    vocabulary: list[str] = Field(default_factory=list, max_length=15)
    exercises: list[ExerciseInput] = Field(default_factory=list, max_length=12)
    module_title: str | None = Field(default=None, min_length=3, max_length=160)
    estimated_minutes: int = Field(default=6, ge=5, le=45)
    grammar: list[GrammarInput] = Field(default_factory=list, max_length=3)
    prerequisites: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_task(self):
        if (self.skill == "writing") != (len(self.exercises) == 0):
            raise ValueError("Writing has an open response; objective tasks require exercises")
        if len({item.key for item in self.exercises}) != len(self.exercises):
            raise ValueError("Exercise keys must be unique")
        if self.skill == "vocabulary" and not self.vocabulary:
            raise ValueError("Vocabulary tasks require existing lexical references")
        if len(set(self.vocabulary)) != len(self.vocabulary):
            raise ValueError("Vocabulary references must be unique")
        if self.skill == "grammar" and not self.grammar:
            raise ValueError("Grammar tasks require authored rules and examples")
        if any(not re.fullmatch(r"[a-z][a-z0-9-]{1,70}", item.slug) for item in self.grammar):
            raise ValueError("Use a bounded grammar slug suitable for a versioned release")
        return self


class AssessmentPack(Strict):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$", max_length=16)
    level: CEFR
    status: Literal["draft"]
    source_license: str = Field(min_length=10, max_length=200)
    tasks: list[AssessmentTask] = Field(min_length=1, max_length=12)
    title: str | None = Field(default=None, min_length=5, max_length=180)
    glossary: list[VocabularyInput] = Field(default_factory=list, max_length=60)
    learning_stage: Literal['A0'] | None = None

    @model_validator(mode="after")
    def unique_tasks(self):
        if len({task.key for task in self.tasks}) != len(self.tasks):
            raise ValueError("Task keys must be unique")
        earlier=set()
        for task in self.tasks:
            if len(task.prerequisites)!=len(set(task.prerequisites)) or not set(task.prerequisites)<=earlier:
                raise ValueError('Prerequisites must identify unique earlier lessons in this release')
            earlier.add(task.key)
        if self.learning_stage=='A0' and self.level!='A1':
            raise ValueError('A0 is introductory A1 preparation, not a stored CEFR level')
        lemmas = [unicodedata.normalize("NFKC", word.lemma).casefold() for word in self.glossary]
        if len(lemmas) != len(set(lemmas)):
            raise ValueError("Glossary identities must be unique")
        references = {lemma for task in self.tasks for lemma in task.vocabulary}
        if not {word.lemma for word in self.glossary} <= references:
            raise ValueError("Every authored glossary entry must be linked to a lesson")
        topics = [item.slug for task in self.tasks for item in task.grammar]
        if len(topics) != len(set(topics)):
            raise ValueError("Each authored grammar identity must have one definition per release")
        return self


def pack_digest(pack):
    """Retain the original release hashes when optional authoring fields are absent."""
    excluded = {name: True for name in ("title", "glossary", "learning_stage") if not getattr(pack, name)}
    excluded["tasks"] = {
        i: {name for name, default in (("module_title", None), ("estimated_minutes", 6), ("grammar", []), ("prerequisites", []))
            if getattr(task, name) == default}
        for i, task in enumerate(pack.tasks)
    }
    return hashlib.sha256(pack.model_dump_json(exclude=excluded).encode()).hexdigest()


def load_assessment_pack(path=CONTENT_PATH):
    return AssessmentPack.model_validate_json(path.read_text(encoding="utf-8"))


def import_assessment_pack(db, pack):
    """Create a separate immutable draft release; never edit enrolled content."""
    key = f"m10-assessments-{pack.level.lower()}-{pack.version}"
    digest = pack_digest(pack)
    batch = db.scalar(select(ImportBatch).where(ImportBatch.batch_key == key))
    if batch:
        if batch.report.get("source_sha256") != digest:
            raise ValueError("Increment the assessment release version before editing content")
        return dict(reused=True, lessons=len(pack.tasks), source_sha256=digest)
    # Resolve references before making any changes. The caller owns the transaction.
    words = {}
    additions = {word.lemma: word for word in pack.glossary}
    for task in pack.tasks:
        for lemma in task.vocabulary:
            matches = db.scalars(select(Lexeme).where(Lexeme.lemma == lemma)).all()
            if not matches and lemma in additions:
                continue
            if len(matches) != 1:
                raise ValueError("Assessment vocabulary must identify one existing lexeme")
            words[lemma] = matches[0]
    # Existing lexical meanings are read-only; a draft cannot rewrite shared vocabulary.
    for lemma, entry in additions.items():
        existing = db.scalars(select(Lexeme).where(Lexeme.lemma == lemma)).all()
        if existing:
            if len(existing) != 1 or existing[0].part_of_speech != entry.part_of_speech or existing[0].grammatical_gender != entry.grammatical_gender:
                raise ValueError("Glossary conflicts with an existing lexical identity")
            sense = db.scalar(select(WordSense).where(WordSense.lexeme_id == existing[0].id,
                WordSense.definition_french == entry.definition_french,
                WordSense.explanation_english == entry.translation))
            if sense is None:
                raise ValueError("A draft cannot replace an existing lexical meaning")
            words[lemma] = existing[0]
    if db.scalar(select(Course).where(Course.slug == key)):
        raise ValueError("Assessment release exists without its immutable import batch")
    source = _upsert(db, ContentSource, {"source_name": f"FluentLoop assessment draft {key}"}, dict(
        source_type="ai_assisted_draft", source_license=pack.source_license, source_url=None,
        attribution_requirements="Original AI-assisted development material. Five independent reviews pending."))
    batch = ImportBatch(source_id=source.id, batch_key=key, content_version=pack.version,
                        status="running", report={})
    db.add(batch)
    db.flush()
    for lemma, entry in additions.items():
        if lemma in words:
            continue
        word = Lexeme(lemma=lemma, normalized_lemma=unicodedata.normalize("NFKC", lemma).casefold(),
            part_of_speech=entry.part_of_speech, grammatical_gender=entry.grammatical_gender,
            irregularity_notes=entry.irregularity_notes)
        db.add(word); db.flush()
        sense = WordSense(lexeme_id=word.id, sense_number=1, definition_french=entry.definition_french,
            explanation_english=entry.translation, usage_notes=entry.teaching_note)
        db.add(sense); db.flush()
        db.add(Translation(word_sense_id=sense.id, language_code="en", translated_text=entry.translation))
        words[lemma] = word
        _provenance(db, source, batch, "lexeme", f"{key}:{lemma}", pack.version)
    course = _upsert(db, Course, {"slug": key}, dict(level_id=pack.level,
        title=pack.title or "French skill assessment drafts", description="Original development assessment tasks awaiting independent review.",
        explanation_language="en", estimated_minutes=sum(task.estimated_minutes for task in pack.tasks) if pack.title else 20,
        status="draft", content_version=pack.version))
    units = {}
    created_lessons = {}
    for order, task in enumerate(pack.tasks, 1):
        module = task.module_title or "Everyday French"
        if module not in units:
            number = len(units) + 1
            units[module] = _upsert(db, Unit, {"course_id": course.id,
                "slug": f"{key}-unit-{number}" if task.module_title else key}, dict(
                title=module, description="Draft learning tasks awaiting independent review.",
                sequence_order=number, status="draft"))
        unit = units[module]
        lesson = _upsert(db, Lesson, {"unit_id": unit.id, "slug": f"{key}-{task.key}"}, dict(
            title=task.title, description=task.objective, estimated_minutes=task.estimated_minutes, sequence_order=order,
            difficulty_level=pack.level, explanation_language="en", content_version=pack.version, status="draft"))
        created_lessons[task.key]=lesson
        for prerequisite in task.prerequisites:
            _upsert(db,LessonPrerequisite,{'lesson_id':lesson.id,'prerequisite_id':created_lessons[prerequisite].id},{})
        objective = _upsert(db, LearningObjective, {"code": f"{key}-{task.key}"}, dict(
            level=pack.level, title=task.title, description=task.objective, skill_category=task.skill))
        _upsert(db, LessonObjective, {"lesson_id": lesson.id, "objective_id": objective.id}, {})
        _upsert(db, LessonSection, {"lesson_id": lesson.id, "sequence_order": 1}, dict(
            section_type="practice", title=f"{task.skill.capitalize()} task", body_content=task.context,
            content_metadata={"assessment_skill": task.skill, "independent_human_review": False,
                              **({'learning_stage':pack.learning_stage} if pack.learning_stage else {})}))
        topics = []
        for grammar in task.grammar:
            topic = _upsert(db, GrammarTopic, {"slug": f"{key}-{grammar.slug}"}, dict(
                title=grammar.title, cefr_level=pack.level, summary=grammar.summary,
                publication_status="draft", teaching_metadata={"independent_human_review": False,
                    "curriculum_supplement": True, "when_to_use": task.objective,
                    "preferred_lesson_slug": lesson.slug, "rule_code": grammar.rule_code}))
            rule = _upsert(db, GrammarRule, {"topic_id": topic.id, "rule_code": grammar.rule_code},
                dict(explanation_english=grammar.explanation_english))
            for french, english in grammar.examples:
                _upsert(db, GrammarExample, {"rule_id": rule.id, "french_sentence": french,
                    "english_translation": english}, {})
            _upsert(db, LessonGrammar, {"lesson_id": lesson.id, "grammar_topic_id": topic.id}, {})
            _provenance(db, source, batch, "grammar_topic", topic.slug, pack.version)
            topics.append(topic)
        for position, lemma in enumerate(task.vocabulary, 1):
            _upsert(db, LessonVocabulary, {"lesson_id": lesson.id, "lexeme_id": words[lemma].id},
                    dict(sequence_order=position, teaching_note="Authored vocabulary linked to this draft task."))
        for position, item in enumerate(task.exercises, 1):
            exercise = _upsert(db, Exercise, {"lesson_id": lesson.id, "sequence_order": position}, dict(
                exercise_type=item.type, prompt=item.prompt, instructions=item.instructions,
                explanation=item.explanation, level=pack.level, exercise_data=item.data,
                learning_objective_id=objective.id, grammar_topic_id=topics[0].id if topics else None))
            for index, label in enumerate(item.options):
                _upsert(db, ExerciseOption, {"exercise_id": exercise.id, "sequence_order": index + 1},
                        dict(option_text=label, is_correct=index == item.correct_option))
            _provenance(db, source, batch, "exercise", f"{key}:{task.key}:{item.key}", pack.version)
        _provenance(db, source, batch, "lesson", lesson.slug, pack.version)
    _provenance(db, source, batch, "course", course.slug, pack.version)
    batch.status = "completed"
    batch.report = dict(source_sha256=digest, review_status="pending", published_lessons=0)
    db.flush()
    return dict(reused=False, lessons=len(pack.tasks), source_sha256=digest)
