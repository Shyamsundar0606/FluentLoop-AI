from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, Request, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import AuthContext, current_auth_context, require_csrf
from app.learning_schemas import (
    AnswerResponse,
    CompletionResponse,
    LearningDashboardResponse,
    LearningSessionResponse,
    LessonProgressResponse,
    ProgressResponse,
    SessionListResponse,
    StartSessionRequest,
    SubmitAnswerRequest,
    PracticeRequest,
    SessionPositionRequest,
)
from app.services import learning_service
from app.api.v1.speech import limited as speech_limited
from app.api.v1.ai import limited as ai_limited

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get('/access')
def learning_access(context: AuthContext = Depends(current_auth_context)):
    from app.services.draft_preview import can_preview_drafts
    preview=can_preview_drafts(context.user)
    return dict(mode='draft_preview' if preview else 'published_only',
        current_level=context.user.preferences.current_level.upper())


@router.get('/library')
def library(level: Literal['A1','A2','B1','B2','C1','C2'] | None = None,
            context: AuthContext = Depends(current_auth_context),db: Session = Depends(get_db)):
    from app.services.interactive_learning import library
    return library(db,context.user,level or context.user.preferences.current_level.upper())


@router.get('/grammar')
def grammar(level: Literal['A1','A2','B1','B2','C1','C2'] | None = None,
            context: AuthContext = Depends(current_auth_context),db: Session = Depends(get_db)):
    from app.services.interactive_learning import grammar
    return grammar(db,context.user,level or context.user.preferences.current_level.upper())


@router.get('/practice/catalog')
def practice_catalog(level: Literal['A1','A2','B1','B2','C1','C2'] | None = None,
            context: AuthContext = Depends(current_auth_context),db: Session = Depends(get_db)):
    from app.services.interactive_learning import candidates
    level=level or context.user.preferences.current_level.upper()
    from app.services.draft_preview import can_preview_drafts
    preview=can_preview_drafts(context.user)
    items=[]
    for category in ('grammar','sentence_building','listening','mistakes'):
        count=len(candidates(db,context.user,level,category))
        reason=('available' if count else 'no_unresolved_mistakes' if category=='mistakes'
            else 'no_permitted_content' if preview else 'no_published_content')
        items.append(dict(category=category,available_exercises=count,availability_reason=reason))
    return dict(level=level,access_mode='draft_preview' if preview else 'published_only',items=items)


@router.post('/practice/sessions',response_model=LearningSessionResponse)
def practice_start(payload: PracticeRequest,context: AuthContext = Depends(require_csrf),db: Session = Depends(get_db)):
    from app.services.interactive_learning import start
    return start(db,context.user,payload)[0]


@router.get('/mistakes')
def review_mistakes(level: Literal['A1','A2','B1','B2','C1','C2'] | None = None,lesson_id: UUID | None = None,
        context: AuthContext = Depends(current_auth_context),db: Session = Depends(get_db)):
    from app.services.interactive_learning import mistakes
    return mistakes(db,context.user,level or context.user.preferences.current_level.upper(),lesson_id)


@router.get('/sessions/{session_id}/review')
def session_review(session_id: UUID,context: AuthContext = Depends(current_auth_context),db: Session = Depends(get_db)):
    from app.services.interactive_learning import session_review
    return session_review(db,context.user,session_id)


@router.post('/sessions/{session_id}/position',response_model=LearningSessionResponse)
def session_position(session_id: UUID,payload: SessionPositionRequest,
        context: AuthContext = Depends(require_csrf),db: Session = Depends(get_db)):
    return learning_service.set_position(db,user=context.user,session_id=session_id,position=payload.position)


@router.post('/sessions/{session_id}/exercises/{exercise_id}/audio')
def listening_audio(session_id: UUID,exercise_id: UUID,context: AuthContext = Depends(speech_limited),db: Session = Depends(get_db)):
    from app.learning_models import LearningSessionExercise
    from app.speech.providers import get_speech_provider
    from app.speech.asr_provider import SpeechUnavailable
    from fastapi import HTTPException
    session=learning_service._session_for_user(db,session_id,context.user)
    saved=db.get(LearningSessionExercise,exercise_id)
    if not saved or saved.learning_session_id!=session.id or saved.exercise_snapshot['type']!='listening':
        raise HTTPException(404,'Listening exercise not found.')
    text=saved.exercise_snapshot.get('text_fr','')
    if not text or len(text)>300:raise HTTPException(409,'Listening prompt unavailable.')
    try:audio=get_speech_provider().synthesize(text)
    except SpeechUnavailable:raise HTTPException(503,'French audio is temporarily unavailable. Please retry.') from None
    if len(audio)>6_000_000 or not audio.startswith(b'RIFF'):
        raise HTTPException(503,'French audio is temporarily unavailable.')
    return Response(audio,media_type='audio/wav',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})


@router.post('/lessons/{lesson_id}/{action}')
def lesson_action(lesson_id: UUID,action: Literal['tutor','speaking'],request: Request,context: AuthContext = Depends(ai_limited),db: Session = Depends(get_db)):
    from app.ai.orchestrator import create
    from app.ai.response_schemas import CreateConversation
    lesson,_,_,_=learning_service._accessible_lesson(db,lesson_id,context.user)
    if lesson.difficulty_level!=context.user.preferences.current_level.upper():
        raise HTTPException(422,'Select this lesson’s French level in Settings before conversation practice.')
    if action=='speaking':
        from app.services.rate_limit import enforce_rate_limit
        enforce_rate_limit(request,f'speech:{context.user.id}',12,60)
    conversation=create(db,context.user,CreateConversation(title=lesson.title[:120],mode='roleplay' if action=='speaking' else 'grammar',linked_lesson_id=lesson.id))
    if action=='speaking':
        from app.speech.voice_orchestrator import start
        from app.speech.schemas import StartSpeech
        speech=start(db,context.user,StartSpeech(conversation_id=conversation.id))
        return dict(url=f'/voice-practice/conversations/{speech.id}')
    return dict(url=f'/ai-tutor/{conversation.id}')


@router.post("/sessions", response_model=LearningSessionResponse)
def create_learning_session(
    payload: StartSessionRequest,
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> LearningSessionResponse:
    result, created = learning_service.start_session(
        db,
        user=context.user,
        lesson_id=payload.lesson_id,
    )
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return result


@router.get("/sessions", response_model=SessionListResponse)
def list_learning_sessions(
    session_status: Literal["in_progress", "completed", "abandoned"] | None = Query(
        None, alias="status"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    items, total = learning_service.list_user_sessions(
        db,
        user=context.user,
        limit=limit,
        offset=offset,
        status_filter=session_status,
    )
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@router.get("/sessions/{session_id}", response_model=LearningSessionResponse)
def retrieve_learning_session(
    session_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> LearningSessionResponse:
    return learning_service.get_session(db, user=context.user, session_id=session_id)


@router.post("/sessions/{session_id}/resume", response_model=LearningSessionResponse)
def resume_learning_session(
    session_id: UUID,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> LearningSessionResponse:
    return learning_service.resume_session(db, user=context.user, session_id=session_id)


@router.post("/sessions/{session_id}/answers", response_model=AnswerResponse)
def submit_learning_answer(
    session_id: UUID,
    payload: SubmitAnswerRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    return learning_service.submit_answer(
        db,
        user=context.user,
        session_id=session_id,
        session_exercise_id=payload.session_exercise_id,
        selected_option_id=payload.selected_option_id,
        idempotency_key=payload.idempotency_key,
        answer_payload=payload.model_dump(mode='json',exclude_none=True,exclude={'session_exercise_id','idempotency_key','selected_option_id'}),
    )


@router.post("/sessions/{session_id}/complete", response_model=CompletionResponse)
def complete_learning_session(
    session_id: UUID,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> CompletionResponse:
    return learning_service.complete_session(db, user=context.user, session_id=session_id)


@router.get("/sessions/{session_id}/results", response_model=CompletionResponse)
def get_learning_results(
    session_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> CompletionResponse:
    return learning_service.get_completion_results(
        db,
        user=context.user,
        session_id=session_id,
    )


@router.post("/sessions/{session_id}/abandon")
def abandon_learning_session(
    session_id: UUID,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    learning_service.abandon_session(db, user=context.user, session_id=session_id)
    return {"status": "abandoned"}


@router.get("/progress", response_model=ProgressResponse)
def list_learning_progress(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    items, total = learning_service.get_progress_for_user(
        db,
        user=context.user,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "limit": limit, "offset": offset, "total": total}


@router.get("/progress/lessons/{lesson_id}", response_model=LessonProgressResponse)
def retrieve_lesson_progress(
    lesson_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    return learning_service.get_lesson_progress(db, user=context.user, lesson_id=lesson_id)


@router.get("/dashboard", response_model=LearningDashboardResponse)
def learning_dashboard(
    _response: Response,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    return learning_service.get_dashboard(db, user=context.user)
