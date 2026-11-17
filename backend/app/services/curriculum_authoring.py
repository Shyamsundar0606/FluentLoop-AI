"""Draft-only edits and comparisons of genuinely persisted content packets."""
import json
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, delete

from app.content_import import _provenance
from app.course_review import digest_packet, packet, provenance, validate_packet
from app.curriculum_models import ContentSource, Course, CurriculumRevision, Exercise, ExerciseOption, ImportBatch, Lesson, LessonSection, LessonPrerequisite, Unit


class EditVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    expected_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    next_version: str = Field(pattern=r"^\d+\.\d+\.\d+$", max_length=32)


class EditSection(EditVersion):
    section_id: UUID
    body_content: str = Field(min_length=1, max_length=4000)

    @field_validator("body_content")
    @classmethod
    def nonempty_body(cls, value):
        if not value.strip():
            raise ValueError("Draft sections require nonempty content")
        return value


class EditLesson(EditVersion):
    lesson_slug: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    estimated_minutes: int = Field(ge=1, le=180)
    prerequisites: list[UUID] | None = Field(default=None, max_length=50)

    @field_validator("title", "description")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Lesson text cannot be blank")
        return value


class EditResource(EditVersion):
    kind: str = Field(min_length=1, max_length=32)
    resource_id: UUID
    values: dict[str, str | None]


class EditCourse(EditVersion):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    estimated_minutes: int = Field(ge=1, le=10000)
    level: Literal["A1", "A2", "B1", "B2", "C1", "C2"]
    source_license: str = Field(min_length=8, max_length=160)
    attribution: str = Field(min_length=8, max_length=1000)
    source_url: str | None = Field(default=None, max_length=2000)

    @field_validator("source_url")
    @classmethod
    def public_reference(cls, value):
        from urllib.parse import urlsplit
        if value is not None:
            parsed = urlsplit(value)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Use an HTTP(S) attribution reference without credentials")
        return value


class OptionEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: UUID
    option_text: str = Field(min_length=1, max_length=1000)
    is_correct: bool


class EditExercise(EditVersion):
    exercise_id: UUID
    prompt: str = Field(min_length=4, max_length=1000)
    instructions: str = Field(min_length=4, max_length=1000)
    explanation: str = Field(min_length=4, max_length=1000)
    data: dict
    options: list[OptionEdit] = Field(max_length=12)


def load_course(db, slug, lock=False):
    query = select(Course).where(Course.slug == slug)
    course = db.scalar(query.with_for_update() if lock else query)
    source = provenance(db, course) if course else None
    if source is None:
        raise HTTPException(404, "Authored course unavailable.")
    return course, source


def save_revision(db, user, course, content):
    digest = digest_packet(content)
    row = db.scalar(select(CurriculumRevision).where(
        CurriculumRevision.course_id == course.id, CurriculumRevision.digest == digest))
    if row is None:
        if len(json.dumps(content).encode()) > 2_000_000:
            raise HTTPException(422, "This packet exceeds the version workspace limit.")
        row = CurriculumRevision(course_id=course.id, content_version=course.content_version,
                                 digest=digest, packet=content, created_by=user.id)
        db.add(row)
        db.flush()
    return row


def revision_view(row):
    return dict(id=str(row.id), version=row.content_version, digest=row.digest, created_at=row.created_at)


def snapshot(db, user, slug):
    course, source = load_course(db, slug, lock=True)
    row = save_revision(db, user, course, packet(db, course, source))
    result = revision_view(row)
    db.commit()
    return result


def history(db, slug, limit, offset):
    course, _ = load_course(db, slug)
    rows = db.scalars(select(CurriculumRevision).where(CurriculumRevision.course_id == course.id)
        .order_by(CurriculumRevision.created_at.desc(), CurriculumRevision.id.desc())
        .offset(offset).limit(limit + 1)).all()
    return dict(items=[revision_view(row) for row in rows[:limit]],
                next_offset=offset + limit if len(rows) > limit else None)


def edit(db, user, slug, payload):
    def apply(lessons):
        section = db.scalar(select(LessonSection).where(LessonSection.id == payload.section_id,
                            LessonSection.lesson_id.in_([lesson.id for lesson in lessons])))
        if section is None:
            raise HTTPException(404, "Draft section not found.")
        section.body_content = payload.body_content
    return edit_version(db, user, slug, payload, apply)


def edit_lesson(db, user, slug, payload):
    def apply(lessons):
        lesson = next((row for row in lessons if row.slug == payload.lesson_slug), None)
        if lesson is None:
            raise HTTPException(404, "Draft lesson not found.")
        lesson.title, lesson.description = payload.title, payload.description
        lesson.estimated_minutes = payload.estimated_minutes
        if payload.prerequisites is not None:
            units = {row.id: row.sequence_order for row in db.scalars(select(Unit).where(
                Unit.id.in_([row.unit_id for row in lessons])))}
            order = lambda row: (units[row.unit_id], row.sequence_order)
            allowed = {row.id for row in lessons if order(row) < order(lesson)}
            if len(set(payload.prerequisites)) != len(payload.prerequisites) or not set(payload.prerequisites) <= allowed:
                raise HTTPException(422, "Prerequisites must be unique earlier lessons in this course; forward links and cycles are not allowed.")
            db.execute(delete(LessonPrerequisite).where(LessonPrerequisite.lesson_id == lesson.id))
            db.add_all([LessonPrerequisite(lesson_id=lesson.id, prerequisite_id=value) for value in payload.prerequisites])
    return edit_version(db, user, slug, payload, apply)


def edit_exercise(db, user, slug, payload):
    def apply(lessons):
        exercise = db.scalar(select(Exercise).where(Exercise.id == payload.exercise_id,
                             Exercise.lesson_id.in_([lesson.id for lesson in lessons])))
        if exercise is None:
            raise HTTPException(404, "Draft exercise not found.")
        options = db.scalars(select(ExerciseOption).where(ExerciseOption.exercise_id == exercise.id)).all()
        if (len(payload.options) != len(options)
                or {row.id for row in payload.options} != {row.id for row in options}):
            raise HTTPException(422, "Preserve the existing option identifiers; create a new exercise for different choices.")
        from app.services.exercise_formats import definition
        try:
            data = definition(exercise.exercise_type, payload.data)
        except ValueError:
            raise HTTPException(422, "Invalid exercise definition for this format.") from None
        exercise.prompt, exercise.instructions = payload.prompt, payload.instructions
        exercise.explanation, exercise.exercise_data = payload.explanation, data
        edits = {row.id: row for row in payload.options}
        for option in options:
            option.option_text, option.is_correct = edits[option.id].option_text, edits[option.id].is_correct
    return edit_version(db, user, slug, payload, apply)


def edit_resource(db, user, slug, payload):
    from app.services.curriculum_resources import edit_resource as apply_resource
    return edit_version(db, user, slug, payload,
                        lambda lessons: apply_resource(db, [row.id for row in lessons], payload))


def edit_course(db, user, slug, payload):
    def apply(lessons):
        course, source = load_course(db, slug)
        if payload.level != course.level_id:
            raise HTTPException(422, "Reclassify through a separate draft release with matching objectives and grammar levels.")
        course.title, course.description = payload.title, payload.description
        course.estimated_minutes = payload.estimated_minutes
        original = db.get(ContentSource, source.source_id)
        updated = ContentSource(source_name=f"staff:{course.id}:{payload.next_version}",
            source_type=original.source_type, source_url=payload.source_url,
            source_license=payload.source_license, attribution_requirements=payload.attribution)
        db.add(updated)
        db.flush()
        return updated
    return edit_version(db, user, slug, payload, apply)


def edit_version(db, user, slug, payload, apply):
    course, source = load_course(db, slug, lock=True)
    before = packet(db, course, source)
    if digest_packet(before) != payload.expected_digest:
        raise HTTPException(409, "This draft changed. Reload the current packet before editing.")
    try:
        increased = tuple(map(int, payload.next_version.split("."))) > tuple(map(int, course.content_version.split(".")))
    except ValueError:
        increased = False
    if not increased:
        raise HTTPException(422, "Use a higher semantic content version.")
    lessons = db.scalars(select(Lesson).join(Unit).where(Unit.course_id == course.id)).all()
    units = db.scalars(select(Unit).where(Unit.course_id == course.id)).all()
    if any(row.status not in ("draft", "review") for row in [course, *units, *lessons]):
        raise HTTPException(409, "Only fully unpublished draft courses can be edited here.")
    save_revision(db, user, course, before)
    updated_source = apply(lessons)
    course.content_version, course.status = payload.next_version, "draft"
    for lesson in lessons:
        lesson.content_version, lesson.status = payload.next_version, "draft"
    for unit in units:
        unit.status = "draft"
    content_source = updated_source if isinstance(updated_source, ContentSource) else db.get(ContentSource, source.source_id)
    batch = ImportBatch(source_id=content_source.id, batch_key=f"staff-edit:{course.id}:{payload.next_version}",
        content_version=payload.next_version, status="completed", report={"review_status": "pending", "origin": "staff_edit"})
    db.add(batch)
    db.flush()
    _provenance(db, content_source, batch, "course", course.slug, payload.next_version)
    for lesson in lessons:
        _provenance(db, content_source, batch, "lesson", lesson.slug, payload.next_version)
    current_source = provenance(db, course)
    after = packet(db, course, current_source)
    issues = validate_packet(after)
    if issues:
        raise HTTPException(422, dict(message="Draft validation failed.", issues=issues))
    row = save_revision(db, user, course, after)
    result = revision_view(row)
    db.commit()
    return result


def flatten(value, path=""):
    if isinstance(value, dict) and value:
        result = {}
        for key, child in value.items():
            result.update(flatten(child, f"{path}.{key}" if path else key))
        return result
    if isinstance(value, list) and value:
        result = {}
        for index, child in enumerate(value):
            result.update(flatten(child, f"{path}[{index}]"))
        return result
    return {path: value}


def compare(db, slug, before_id, after_id):
    course, _ = load_course(db, slug)
    rows = db.scalars(select(CurriculumRevision).where(CurriculumRevision.course_id == course.id,
        CurriculumRevision.id.in_([before_id, after_id]))).all()
    found = {row.id: row for row in rows}
    if before_id not in found or after_id not in found:
        raise HTTPException(404, "Stored version not found for this course.")
    before, after = flatten(found[before_id].packet), flatten(found[after_id].packet)
    changes = [dict(path=path, before=before.get(path), after=after.get(path),
                    before_exists=path in before, after_exists=path in after)
               for path in sorted(before.keys() | after.keys()) if path not in before or path not in after or before[path] != after[path]]
    return dict(before=revision_view(found[before_id]), after=revision_view(found[after_id]),
                changes=changes[:1000], total_changes=len(changes))
