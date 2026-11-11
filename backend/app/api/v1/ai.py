from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import AuthContext, current_auth_context, require_csrf
from app.ai.models import Conversation, PracticeFeedback
from app.ai.response_schemas import (
    CreateConversation,
    RenameConversation,
    SendMessage,
    CorrectionRequest,
    ConversationView,
    ChatResponse,
    Mode,
    Level,
    CoachOptions,
)
from app.ai.response_schemas import HealthView, RecommendationView, FeedbackView
from app.ai import orchestrator as service, recommendations
from app.ai import coach
from app.ai.providers.ollama_provider import get_provider
from app.ai.providers.base import ProviderUnavailable
from app.ai.scenarios import SCENARIOS, scenario_by_id, Scenario
from app.services.rate_limit import enforce_rate_limit
from app.models import utcnow

router = APIRouter(prefix="/ai", tags=["AI French tutor"])


def provider_dependency():
    try:
        return get_provider()
    except ProviderUnavailable:
        raise HTTPException(503, "AI provider is not configured.") from None


def limited(request: Request, context: AuthContext = Depends(require_csrf)):
    enforce_rate_limit(request, f"ai:{context.user.id}", 30, 60)
    return context


@router.get("/health", response_model=HealthView)
def health(context: AuthContext = Depends(current_auth_context)):
    try:
        available = get_provider().health()
    except ProviderUnavailable:
        available = False
    return {
        "available": available,
        "provider": "ollama",
        "message": (
            "Ready"
            if available
            else "Configured model unavailable. Regular lessons remain available."
        ),
    }


@router.post("/conversations", response_model=ConversationView, status_code=201)
def create(
    payload: CreateConversation,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
):
    return service.create(db, context.user, payload)


@router.get("/conversations", response_model=list[ConversationView])
def list_conversations(
    mode: Mode | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    query = select(Conversation).where(Conversation.user_id == context.user.id)
    if mode:
        query = query.where(Conversation.mode == mode)
    rows = db.scalars(
        query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
    ).all()
    result = []
    for c in rows:
        try:
            service.owned(db, context.user, c.id)
            result.append(service.conversation_view(db, context.user, c))
        except HTTPException:
            continue
    return result


@router.get("/conversations/{conversation_id}", response_model=ConversationView)
def get_conversation(
    conversation_id: UUID,
    before: UUID | None = None,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    c = service.owned(db, context.user, conversation_id)
    return service.conversation_view(db, context.user, c, True, before)


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
def message(
    conversation_id: UUID,
    payload: SendMessage,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
    provider=Depends(provider_dependency),
):
    return service.send(db, context.user, conversation_id, payload, provider)


@router.patch("/conversations/{conversation_id}", response_model=ConversationView)
def rename(
    conversation_id: UUID,
    payload: RenameConversation,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
):
    c = service.owned(db, context.user, conversation_id)
    c.title = payload.title
    c.updated_at = utcnow()
    db.commit()
    return service.conversation_view(db, context.user, c)


@router.post(
    "/conversations/{conversation_id}/archive", response_model=ConversationView
)
def archive(
    conversation_id: UUID,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
):
    c = service.owned(db, context.user, conversation_id)
    c.status = "archived"
    c.updated_at = utcnow()
    db.commit()
    return service.conversation_view(db, context.user, c)


@router.get("/conversations/{conversation_id}/coach")
def coach_session(conversation_id: UUID, context: AuthContext = Depends(current_auth_context),
                  db: Session = Depends(get_db)):
    conversation = service.owned(db, context.user, conversation_id)
    scenario = scenario_by_id(conversation.scenario_id)
    evidence = coach.evidence(db, context.user, conversation.cefr_level, conversation.id)
    return {
        "scenario": scenario,
        "scenario_vocabulary": coach.scenario_words(scenario),
        "due_vocabulary": evidence["due_vocabulary"],
        "studied_vocabulary": evidence["studied_vocabulary"],
        "studied_grammar": evidence["studied_grammar"],
        "summary": coach.summary(db, conversation, scenario) if conversation.completed_at else None,
    }


@router.patch("/conversations/{conversation_id}/coach", response_model=ConversationView)
def coach_options(conversation_id: UUID, payload: CoachOptions, context: AuthContext = Depends(limited),
                  db: Session = Depends(get_db)):
    conversation = service.owned(db, context.user, conversation_id)
    if payload.difficulty is not None:
        if conversation.status != "active":
            raise HTTPException(409, "This conversation is closed.")
        conversation.coach_difficulty = payload.difficulty
    if payload.corrections is not None:
        context.user.preferences.coach_corrections = payload.corrections
    db.commit()
    return service.conversation_view(db, context.user, conversation)


@router.post("/conversations/{conversation_id}/finish", response_model=ConversationView)
def finish(conversation_id: UUID, context: AuthContext = Depends(limited), db: Session = Depends(get_db)):
    conversation = service.owned(db, context.user, conversation_id)
    if not conversation.completed_at:
        now = utcnow()
        updated = db.execute(update(Conversation).where(
            Conversation.id == conversation.id, Conversation.status == "active",
            Conversation.active_request_id.is_(None),
        ).values(status="archived", completed_at=now, updated_at=now)).rowcount
        if not updated:
            db.refresh(conversation)
            if not conversation.completed_at:
                raise HTTPException(409, "Wait for the current reply or reopen an active conversation.")
        db.commit()
    return service.conversation_view(db, context.user, conversation)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, context: AuthContext = Depends(limited), db: Session = Depends(get_db)):
    # Allow deletion even if an old draft citation is no longer readable.
    conversation = db.scalar(select(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == context.user.id).with_for_update())
    if not conversation:
        raise HTTPException(404, "Conversation not found.")
    if conversation.active_request_id:
        raise HTTPException(409, "Wait for the current reply before deleting.")
    db.delete(conversation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This conversation is linked to saved speaking or study history.") from None


@router.get("/scenarios", response_model=list[Scenario])
def scenarios(
    level: Level | None = None, context: AuthContext = Depends(current_auth_context)
):
    return [
        s
        for s in SCENARIOS
        if s.cefr_level == (level or context.user.preferences.current_level.upper())
    ]


@router.post(
    "/scenarios/{scenario_id}/start", response_model=ConversationView, status_code=201
)
def start(
    scenario_id: str,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
):
    scenario = scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found.")
    return service.create(db, context.user, CreateConversation(), scenario)


@router.post("/corrections", response_model=ChatResponse)
def correction(
    payload: CorrectionRequest,
    context: AuthContext = Depends(limited),
    db: Session = Depends(get_db),
    provider=Depends(provider_dependency),
):
    c = service.owned(db, context.user, payload.conversation_id)
    if c.mode != "correction":
        raise HTTPException(422, "Use a sentence correction conversation.")
    return service.send(
        db,
        context.user,
        c.id,
        SendMessage(message=payload.message, request_id=payload.request_id),
        provider,
    )


@router.get("/recommendations", response_model=list[RecommendationView])
def get_recommendations(
    context: AuthContext = Depends(current_auth_context), db: Session = Depends(get_db)
):
    return recommendations.list_recommendations(db, context.user)


@router.post("/recommendations/refresh", response_model=list[RecommendationView])
def refresh_recommendations(
    context: AuthContext = Depends(limited), db: Session = Depends(get_db)
):
    return recommendations.refresh(db, context.user)


@router.get(
    "/conversations/{conversation_id}/feedback", response_model=list[FeedbackView]
)
def feedback(
    conversation_id: UUID,
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
):
    service.owned(db, context.user, conversation_id)
    rows = db.scalars(
        select(PracticeFeedback)
        .where(
            PracticeFeedback.conversation_id == conversation_id,
            PracticeFeedback.user_id == context.user.id,
        )
        .order_by(PracticeFeedback.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": str(r.id),
            "cefr_level": r.cefr_level,
            "topic": r.topic,
            "feedback_type": r.feedback_type,
            "corrected_text": r.corrected_text,
            "explanation": r.explanation,
        }
        for r in rows
    ]
