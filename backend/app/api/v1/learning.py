from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
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
)
from app.services import learning_service

router = APIRouter(prefix="/learning", tags=["learning"])


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
