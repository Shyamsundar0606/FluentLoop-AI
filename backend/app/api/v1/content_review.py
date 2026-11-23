"""Authenticated review queue and versioned decisions in the existing API console."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.database import get_db
from app.course_review import ReviewInput, digest_packet, packet, provenance, readiness, record_review, validate_packet
from app.curriculum_models import Course
from app.dependencies import AuthContext, current_auth_context, require_csrf
from app.services.draft_preview import can_author_drafts
from app.services import curriculum_authoring as authoring
from app.assessment_content import AssessmentPack, import_assessment_pack

router = APIRouter(prefix="/content-review", tags=["curriculum review"])


def author_permission(request: Request, context: AuthContext = Depends(require_csrf)):
    if not can_author_drafts(context.user):
        raise HTTPException(403, "Authorized draft authoring access required.")
    from app.services.rate_limit import enforce_rate_limit
    enforce_rate_limit(request, f"authoring:{context.user.id}", 20, 60)
    return context


@router.post("/drafts")
def create_drafts(payload: AssessmentPack, context: AuthContext = Depends(author_permission), db: Session = Depends(get_db)):
    try:
        report = import_assessment_pack(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    slug = f"m10-assessments-{payload.level.lower()}-{payload.version}"
    revision = authoring.snapshot(db, context.user, slug)
    return dict(slug=slug, report=report, revision=revision)


@router.post("/{slug}/revisions")
def save_version(slug: str, context: AuthContext = Depends(author_permission), db: Session = Depends(get_db)):
    return authoring.snapshot(db, context.user, slug)


@router.get("/{slug}/revisions")
def versions(slug: str, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
             context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    inspect_permission(context)
    return authoring.history(db, slug, limit, offset)


@router.get("/{slug}/compare")
def compare_versions(slug: str, before: UUID, after: UUID,
                     context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    inspect_permission(context)
    return authoring.compare(db, slug, before, after)


@router.post("/{slug}/sections")
def edit_section(slug: str, payload: authoring.EditSection,
                 context: AuthContext = Depends(author_permission), db: Session = Depends(get_db)):
    return authoring.edit(db, context.user, slug, payload)


@router.post("/{slug}/lessons")
def edit_lesson(slug: str, payload: authoring.EditLesson,
                context: AuthContext = Depends(author_permission), db: Session = Depends(get_db)):
    return authoring.edit_lesson(db, context.user, slug, payload)


@router.post("/{slug}/exercises")
def edit_exercise(slug: str, payload: authoring.EditExercise,
                  context: AuthContext = Depends(author_permission), db: Session = Depends(get_db)):
    return authoring.edit_exercise(db, context.user, slug, payload)


@router.post("/{slug}/resources")
def edit_resource(slug: str, payload: authoring.EditResource,
                  context: AuthContext = Depends(author_permission), db: Session = Depends(get_db)):
    return authoring.edit_resource(db, context.user, slug, payload)


@router.post("/{slug}/course")
def edit_course(slug: str, payload: authoring.EditCourse,
                context: AuthContext = Depends(author_permission), db: Session = Depends(get_db)):
    return authoring.edit_course(db, context.user, slug, payload)


def grant_for(user):
    if user.role == "admin" or not user.is_active or not user.email_verified_at:
        return None
    return get_settings().curriculum_reviewer_grants.get(user.id)


def inspect_permission(context):
    if not grant_for(context.user) and not can_author_drafts(context.user):
        raise HTTPException(403, "Curriculum review access required.")


def load(db, slug, *, lock=False):
    query = select(Course).where(Course.slug == slug)
    course = db.scalar(query.with_for_update() if lock else query)
    source = provenance(db, course, lock=lock) if course else None
    if source is None:
        raise HTTPException(404, "Review packet unavailable.")
    content = packet(db, course, source)
    return course, source, content, digest_packet(content)


@router.get("/queue")
def queue(context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    inspect_permission(context)
    items = []
    courses = db.scalars(select(Course).where(Course.status.in_(("draft", "review")))
        .order_by(Course.level_id, Course.slug))
    for course in courses:
        source = provenance(db, course)
        if source is not None:
            digest = digest_packet(packet(db, course, source))
            history = source.review_metadata.get("independent_reviews", [])
            items.append(dict(slug=course.slug, title=course.title, level=course.level_id, version=course.content_version,
                              digest=digest, **readiness(history, digest, course.content_version)))
    return {"items": items, "can_author": can_author_drafts(context.user)}


@router.get("/{slug}")
def detail(slug: str, context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    inspect_permission(context)
    course, source, content, digest = load(db, slug)
    history = source.review_metadata.get("independent_reviews", [])
    return dict(content=content, digest=digest, history=history, can_author=can_author_drafts(context.user),
                technical_issues=validate_packet(content),
                categories=sorted(grant_for(context.user).categories) if grant_for(context.user) else [],
                readiness=readiness(history, digest, course.content_version))


@router.post("/{slug}/decisions", status_code=201)
def decide(slug: str, payload: ReviewInput, context: AuthContext = Depends(require_csrf),
           db: Session = Depends(get_db)):
    grant = grant_for(context.user)
    if grant is None or payload.category not in grant.categories:
        raise HTTPException(403, "Independent permission for this review category is required.")
    course, source, _, digest = load(db, slug, lock=True)
    if course.status not in ("draft", "review") or (payload.version, payload.digest) != (course.content_version, digest):
        raise HTTPException(409, "Reload the current draft review packet before submitting.")
    decision = record_review(source, payload, context.user.id, grant)
    db.commit()
    return decision


@router.post("/{slug}/listening")
def listening(slug: str, exercise_id: str, request: Request, context: AuthContext = Depends(require_csrf),
              db: Session = Depends(get_db)):
    inspect_permission(context)
    from app.services.rate_limit import enforce_rate_limit
    from app.speech.asr_provider import SpeechUnavailable
    from app.speech.providers import get_speech_provider

    enforce_rate_limit(request, f"review-audio:{context.user.id}", 12, 60)
    _, _, content, _ = load(db, slug)
    for lesson in content["lessons"]:
        for exercise in lesson["exercises"]:
            if exercise["id"] == exercise_id and exercise["type"] == "listening":
                script = exercise["data"].get("text_fr", "")
                from app.services.exercise_formats import MAX_LISTENING_CHARACTERS
                if not script or len(script) > MAX_LISTENING_CHARACTERS:
                    raise HTTPException(409, "Listening script unavailable.")
                try:
                    audio = get_speech_provider().synthesize(script)
                except SpeechUnavailable:
                    raise HTTPException(503, "French audio is temporarily unavailable.") from None
                if not audio.startswith(b"RIFF") or len(audio) > 6_000_000:
                    raise HTTPException(503, "French audio is temporarily unavailable.")
                return Response(audio, media_type="audio/wav", headers={"Cache-Control": "no-store"})
    raise HTTPException(404, "Listening exercise not found.")
