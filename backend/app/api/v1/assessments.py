from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies import AuthContext, current_auth_context, require_csrf
from app.learning_schemas import LearningSessionResponse
from app.services import assessment_service, writing_service
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/learning/assessments", tags=["assessments"])


class StartAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: Literal["grammar", "vocabulary", "reading", "listening"]
    lesson_id: UUID


@router.get("")
def catalog(level: Literal['A1','A2','B1','B2','C1','C2'] | None = None,
            context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    return assessment_service.catalog(db, context.user, level)


@router.post("/sessions", response_model=LearningSessionResponse)
def start(payload: StartAssessment, request: Request,
          context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db)):
    enforce_rate_limit(request, f"assessment:{context.user.id}", 20, 60)
    return assessment_service.start(db, context.user, payload.skill, payload.lesson_id)


@router.get("/history")
def history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
            context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    return assessment_service.history(db, context.user, limit, offset)


@router.get("/insights")
def insights(context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    result = assessment_service.insights(db, context.user)
    writing = writing_service.history(db, context.user, 100, 0)
    result["writing"] = dict(submissions=sum(item["level"] == result["level"] for item in writing["items"]),
        sample_limit=100, has_older_history=writing["next_offset"] is not None,
        evidence="Saved writing practice; feedback is advisory and unscored.")
    return result


class SubmitWriting(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lesson_id: UUID
    idempotency_key: UUID
    text: str = Field(min_length=1, max_length=writing_service.MAX_WRITING_CHARACTERS)

    @field_validator("text")
    @classmethod
    def nonempty_text(cls, value):
        if not value.strip():
            raise ValueError("Write a response before submitting")
        return value


@router.get("/writing/tasks/{lesson_id}")
def writing_task(lesson_id: UUID, context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    return writing_service.task(db, context.user, lesson_id)


@router.post("/writing")
def submit_writing(payload: SubmitWriting, request: Request,
                   context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db)):
    enforce_rate_limit(request, f"writing:{context.user.id}", 20, 60)
    return writing_service.submit(db, context.user, payload)


@router.get("/writing/history")
def writing_history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0, le=100000),
                    context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    return writing_service.history(db, context.user, limit, offset)


@router.get("/writing/{submission_id}")
def get_writing(submission_id: UUID, context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)):
    return writing_service.view(writing_service.owned(db, context.user, submission_id))


@router.post("/writing/{submission_id}/feedback")
def writing_feedback(submission_id: UUID, request: Request,
                     context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db)):
    enforce_rate_limit(request, f"writing-feedback:{context.user.id}", 5, 60)
    return writing_service.feedback(db, context.user, submission_id)
