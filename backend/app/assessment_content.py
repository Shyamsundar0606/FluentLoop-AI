"""Validated, versioned assessment drafts imported through existing content helpers."""
import hashlib
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from sqlalchemy import select

from app.content_import import _upsert, _provenance
from app.content_schemas import CEFR
from app.curriculum_models import (
    ContentSource, Course, Exercise, ExerciseOption, ImportBatch, LearningObjective,
    Lesson, LessonObjective, LessonSection, LessonVocabulary, Lexeme, Unit,
)
from app.interactive_content import ExerciseInput, Strict

CONTENT_PATH = Path(__file__).resolve().parents[1] / "content/practice/a1-assessments-0.1.0.json"


class AssessmentTask(Strict):
    key: str = Field(pattern=r"^[a-z][a-z0-9-]{2,40}$")
    skill: Literal["vocabulary", "reading", "writing"]
    title: str = Field(min_length=5, max_length=160)
    objective: str = Field(min_length=10, max_length=500)
    context: str = Field(min_length=20, max_length=2000)
    vocabulary: list[str] = Field(default_factory=list, max_length=15)
    exercises: list[ExerciseInput] = Field(default_factory=list, max_length=12)

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
        return self


class AssessmentPack(Strict):
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$", max_length=16)
    level: CEFR
    status: Literal["draft"]
    source_license: str = Field(min_length=10, max_length=200)
    tasks: list[AssessmentTask] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def unique_tasks(self):
        if len({task.key for task in self.tasks}) != len(self.tasks):
            raise ValueError("Task keys must be unique")
        return self


def load_assessment_pack(path=CONTENT_PATH):
    return AssessmentPack.model_validate_json(path.read_text(encoding="utf-8"))


def import_assessment_pack(db, pack):
    """Create a separate immutable draft release; never edit enrolled content."""
    key = f"m10-assessments-{pack.level.lower()}-{pack.version}"
    digest = hashlib.sha256(pack.model_dump_json().encode()).hexdigest()
    batch = db.scalar(select(ImportBatch).where(ImportBatch.batch_key == key))
    if batch:
        if batch.report.get("source_sha256") != digest:
            raise ValueError("Increment the assessment release version before editing content")
        return dict(reused=True, lessons=len(pack.tasks), source_sha256=digest)
    # Resolve references before making any changes. The caller owns the transaction.
    words = {}
    for task in pack.tasks:
        for lemma in task.vocabulary:
            matches = db.scalars(select(Lexeme).where(Lexeme.lemma == lemma)).all()
            if len(matches) != 1:
                raise ValueError("Assessment vocabulary must identify one existing lexeme")
            words[lemma] = matches[0]
    if db.scalar(select(Course).where(Course.slug == key)):
        raise ValueError("Assessment release exists without its immutable import batch")
    source = _upsert(db, ContentSource, {"source_name": f"FluentLoop assessment draft {key}"}, dict(
        source_type="ai_assisted_draft", source_license=pack.source_license, source_url=None,
        attribution_requirements="Original AI-assisted development material. Five independent reviews pending."))
    batch = ImportBatch(source_id=source.id, batch_key=key, content_version=pack.version,
                        status="running", report={})
    db.add(batch)
    db.flush()
    course = _upsert(db, Course, {"slug": key}, dict(level_id=pack.level,
        title="French skill assessment drafts", description="Original development assessment tasks awaiting independent review.",
        explanation_language="en", estimated_minutes=20, status="draft", content_version=pack.version))
    unit = _upsert(db, Unit, {"course_id": course.id, "slug": key}, dict(
        title="Everyday French", description="Draft vocabulary, reading and writing tasks.", sequence_order=1, status="draft"))
    for order, task in enumerate(pack.tasks, 1):
        lesson = _upsert(db, Lesson, {"unit_id": unit.id, "slug": f"{key}-{task.key}"}, dict(
            title=task.title, description=task.objective, estimated_minutes=6, sequence_order=order,
            difficulty_level=pack.level, explanation_language="en", content_version=pack.version, status="draft"))
        objective = _upsert(db, LearningObjective, {"code": f"{key}-{task.key}"}, dict(
            level=pack.level, title=task.title, description=task.objective, skill_category=task.skill))
        _upsert(db, LessonObjective, {"lesson_id": lesson.id, "objective_id": objective.id}, {})
        _upsert(db, LessonSection, {"lesson_id": lesson.id, "sequence_order": 1}, dict(
            section_type="practice", title=f"{task.skill.capitalize()} task", body_content=task.context,
            content_metadata={"assessment_skill": task.skill, "independent_human_review": False}))
        for position, lemma in enumerate(task.vocabulary, 1):
            _upsert(db, LessonVocabulary, {"lesson_id": lesson.id, "lexeme_id": words[lemma].id},
                    dict(sequence_order=position, teaching_note="Existing vocabulary reused for draft assessment."))
        for position, item in enumerate(task.exercises, 1):
            exercise = _upsert(db, Exercise, {"lesson_id": lesson.id, "sequence_order": position}, dict(
                exercise_type=item.type, prompt=item.prompt, instructions=item.instructions,
                explanation=item.explanation, level=pack.level, exercise_data=item.data,
                learning_objective_id=objective.id, grammar_topic_id=None))
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
