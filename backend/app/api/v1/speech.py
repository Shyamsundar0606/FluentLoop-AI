from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
    Query,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import AuthContext, current_auth_context, require_csrf
from app.services.rate_limit import enforce_rate_limit
from app.models import utcnow, User
from app.api.v1.ai import provider_dependency
from app.ai.response_schemas import Level
from app.ai.scenarios import SCENARIOS
from app.speech.providers import get_speech_provider
from app.speech.asr_provider import SpeechUnavailable
from app.speech.schemas import (
    StartSpeech,
    SpeechText,
    Synthesize,
    SpeechSessionView,
    TurnView,
    AttemptView,
    Transcription,
    Target,
    AudioView,
)
from app.speech.models import (
    SpeechSession,
    SpeechTurn,
    PronunciationAttempt,
    SpeechProgress,
)
from app.speech import (
    voice_orchestrator as service,
    storage,
    pronunciation_service as pronunciation,
)
from app.config import get_settings

router = APIRouter(prefix="/speech", tags=["French voice practice"])


def limited(request: Request, context: AuthContext = Depends(require_csrf)):
    enforce_rate_limit(request, f"speech:{context.user.id}", 12, 60)
    return context


async def read_audio(audio: UploadFile):
    data = bytearray()
    try:
        while chunk := await audio.read(65536):
            data.extend(chunk)
            if len(data) > get_settings().speech_max_upload_bytes:
                raise HTTPException(413, "Recording exceeds upload limit.")
    finally:
        await audio.close()
    from app.speech.audio_validation import validate_upload

    validate_upload(bytes(data))
    return bytes(data)


@router.get("/health")
def health(
    context: AuthContext = Depends(current_auth_context),
    speech=Depends(get_speech_provider),
):
    state=speech.health()
    return {
        'asr':bool(state.get('asr')),
        'tts':bool(state.get('tts')),
        "acoustic_assessment": "not_available",
        "max_duration_seconds": get_settings().speech_max_duration_seconds,
        "max_upload_bytes": get_settings().speech_max_upload_bytes,
        "raw_audio_retained_by_default": False,
    }


@router.get("/scenarios")
def scenarios(context: AuthContext = Depends(current_auth_context)):
    return [
        {
            **s.model_dump(),
            "voice_enabled": True,
            "opening_question": s.opening_situation,
        }
        for s in SCENARIOS
        if s.cefr_level == context.user.preferences.current_level.upper()
    ]


@router.post("/transcribe", response_model=Transcription)
async def transcribe(
    audio: UploadFile = File(...),
    context: AuthContext = Depends(limited),
    speech=Depends(get_speech_provider),
):
    from starlette.concurrency import run_in_threadpool

    data = await read_audio(audio)
    try:
        return await run_in_threadpool(speech.transcribe, data)
    except SpeechUnavailable:
        raise HTTPException(503, "French transcription unavailable.") from None


@router.post("/synthesize", response_model=AudioView)
def synthesize(
    payload: Synthesize,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
    speech=Depends(get_speech_provider),
):
    user = context.user
    lesson = None
    session = None
    if payload.session_id:
        session, _ = service.owned(db, user, payload.session_id)
    if payload.target_id:
        lesson = pronunciation.target(db, user, payload.target_id)
        if payload.text != lesson.text:
            raise HTTPException(
                422, "Reference audio must match the authorized target."
            )
    uid = user.id
    version = lesson.content_version if lesson else None
    db.commit()
    try:
        data = speech.synthesize(payload.text)
    except SpeechUnavailable:
        raise HTTPException(503, "French voice unavailable.") from None
    db.expire_all()
    user = db.get(User, uid)
    if not user or not user.is_active:
        raise HTTPException(401, "Authentication required.")
    if session:
        session, _ = service.owned(db, user, payload.session_id)
    if lesson:
        lesson = pronunciation.target(db, user, payload.target_id)
        if lesson.content_version != version:
            raise HTTPException(409, "Target changed.")
    asset = storage.store(
        db,
        user,
        data,
        session=session,
        lesson=lesson,
        source="reference" if lesson else "tutor",
    )
    db.commit()
    return AudioView(
        status="ready",
        asset_id=asset.id,
        spoken_text=payload.text,
        voice=get_settings().speech_tts_voice,
        duration_ms=asset.duration_ms,
    )


@router.get("/sessions", response_model=list[SpeechSessionView])
def sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(SpeechSession)
        .where(SpeechSession.user_id == context.user.id)
        .order_by(SpeechSession.last_activity_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    result = []
    for row in rows:
        try:
            result.append(service.view(db, context.user, row))
        except HTTPException:
            continue
    return result


@router.post("/sessions", response_model=SpeechSessionView, status_code=201)
def start(
    payload: StartSpeech,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
):
    return service.start(db, context.user, payload)


@router.get("/sessions/{sid}", response_model=SpeechSessionView)
@router.get("/sessions/{sid}/history", response_model=SpeechSessionView)
def get_session(
    sid: UUID,
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    session, _ = service.owned(db, context.user, sid)
    return service.view(db, context.user, session, True, offset)


@router.post("/sessions/{sid}/turns", response_model=TurnView)
def turn(
    sid: UUID,
    request_id: UUID = Form(...),
    retain_audio: bool = Form(False),
    audio: UploadFile = File(...),
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
    speech=Depends(get_speech_provider),
    ai_provider=Depends(provider_dependency),
):
    # UploadFile is already spooled under the request cap; decode occurs in worker.
    service.owned(db, context.user, sid)
    try:
        data = audio.file.read(get_settings().speech_max_upload_bytes + 1)
        return service.submit(
            db,
            context.user,
            sid,
            request_id,
            speech,
            ai_provider,
            data=data,
            retain=retain_audio,
        )
    finally:
        audio.file.close()


@router.post("/sessions/{sid}/text", response_model=TurnView)
def text_turn(
    sid: UUID,
    payload: SpeechText,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
    speech=Depends(get_speech_provider),
    ai_provider=Depends(provider_dependency),
):
    return service.submit(
        db,
        context.user,
        sid,
        payload.request_id,
        speech,
        ai_provider,
        text=payload.message,
        reviewed_turn_id=payload.reviewed_turn_id,
    )


@router.post("/sessions/{sid}/turns/{tid}/audio", response_model=TurnView)
def retry_audio(
    sid: UUID,
    tid: UUID,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
    speech=Depends(get_speech_provider),
):
    try:
        return service.retry_audio(db, context.user, sid, tid, speech)
    except SpeechUnavailable:
        raise HTTPException(
            503, "French voice unavailable; saved tutor text is unchanged."
        ) from None


@router.post("/sessions/{sid}/complete", response_model=SpeechSessionView)
def complete(
    sid: UUID, context: AuthContext = Depends(limited), db: Session = Depends(get_db)
):
    session, _ = service.owned(db, context.user, sid)
    if session.active_request_id:
        raise HTTPException(409, "Wait for the current turn to finish.")
    session.status = "completed"
    session.completed_at = utcnow()
    session.updated_at = utcnow()
    db.commit()
    return service.view(db, context.user, session, True)


@router.get("/pronunciation/targets", response_model=list[Target])
def targets(
    level: Level | None = None,
    limit: int = Query(30, ge=1, le=100),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    return pronunciation.targets(db, context.user, level, limit)


@router.get("/pronunciation/targets/{target_id}", response_model=Target)
def target(
    target_id: str,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    return pronunciation.target(db, context.user, target_id)


@router.post("/pronunciation/attempts", response_model=AttemptView)
def attempt(
    request_id: UUID = Form(...),
    target_id: str = Form(..., max_length=100),
    retain_audio: bool = Form(False),
    audio: UploadFile = File(...),
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
    speech=Depends(get_speech_provider),
):
    pronunciation.target(db, context.user, target_id)
    try:
        return service.attempt(
            db,
            context.user,
            target_id,
            request_id,
            audio.file.read(get_settings().speech_max_upload_bytes + 1),
            retain_audio,
            speech,
        )
    except SpeechUnavailable:
        raise HTTPException(503, "French transcription unavailable.") from None
    finally:
        audio.file.close()


@router.get("/pronunciation/history", response_model=list[AttemptView])
def attempts(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    target_id: str | None = Query(None, max_length=100),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(PronunciationAttempt)
        .where(PronunciationAttempt.user_id == context.user.id)
        .where(PronunciationAttempt.target_id == target_id if target_id else True)
        .order_by(PronunciationAttempt.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    result = []
    for row in rows:
        try:
            result.append(service.attempt_view(db, context.user, row))
        except HTTPException:
            continue
    return result


@router.get("/pronunciation/progress")
def progress(
    context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)
):
    rows = db.scalars(
        select(SpeechProgress)
        .where(SpeechProgress.user_id == context.user.id)
        .order_by(SpeechProgress.last_practiced_at.desc())
        .limit(100)
    ).all()
    result = []
    for row in rows:
        try:
            target = pronunciation.target(db, context.user, row.target_id)
            if target.content_version != row.content_version:
                continue
            result.append(
                {
                    "target": target.model_dump(mode="json"),
                    "attempt_count": row.attempt_count,
                    "last_practiced_at": row.last_practiced_at,
                    "latest_assessment_status": row.latest_assessment_status,
                    "latest_validated_score": None,
                }
            )
        except HTTPException:
            continue
    return result


@router.get("/audio/{asset_id}")
def audio(
    asset_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    asset = storage.owned_audio(db, context.user, asset_id)
    path = storage.path_for(asset.storage_key)
    if not path.is_file():
        raise HTTPException(404, "Audio not available.")
    return FileResponse(
        path,
        media_type=asset.media_type,
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.delete("/audio/{asset_id}")
def delete_audio(
    asset_id: UUID,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
):
    asset = storage.owned_audio(db, context.user, asset_id, allow_deleted=True)
    storage.delete(db, asset)
    db.commit()
    return {"status": "deleted"}
