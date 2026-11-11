import json
import logging
from datetime import timedelta
from uuid import uuid4, UUID

from fastapi import HTTPException
from sqlalchemy import select, update, or_, func
from pydantic import ValidationError

from app.ai.models import Conversation, Message, MessageSource, PracticeFeedback
from app.ai.response_schemas import (
    ConversationView,
    MessageView,
    ChatResponse,
    Correction,
    ScenarioReply,
)
from app.ai.coach import evidence
from app.ai.providers.base import Generation
from app.ai.retrieval import source_for, retrieve
from app.ai.prompts import build_messages, first_name_hint
from app.ai.scenarios import LANGUAGE_ONLY_TURNS, scenario_by_id
from app.ai.providers.base import ProviderUnavailable
from app.config import get_settings
from app.models import User, utcnow
from app.services.draft_preview import can_preview_drafts

logger = logging.getLogger(__name__)


def owned(db, user, conversation_id):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user.id
        )
    )
    if not conversation:
        raise HTTPException(404, "Conversation not found.")
    if conversation.preview_mode and not can_preview_drafts(user):
        raise HTTPException(404, "Conversation not available.")
    if conversation.linked_lesson_id:
        source_for(db, user, conversation.linked_lesson_id)
    # Revalidate every historical source before exposing text or reusing memory.
    refs = db.execute(
        select(MessageSource.source_record_id, MessageSource.content_version)
        .join(Message, Message.id == MessageSource.message_id)
        .where(Message.conversation_id == conversation.id)
        .distinct()
    ).all()
    for lesson_id, version in refs:
        source = source_for(db, user, lesson_id)
        if source.content_version != version:
            raise HTTPException(
                409, "Source content changed. Start a new conversation."
            )
    return conversation


def sources_for_message(db, user, message_id):
    refs = db.scalars(
        select(MessageSource)
        .where(MessageSource.message_id == message_id)
        .order_by(MessageSource.id)
    ).all()
    return [source_for(db, user, ref.source_record_id) for ref in refs]


def conversation_view(db, user, c, messages=False, before=None):
    view = ConversationView.model_validate(c)
    view.coach_corrections = user.preferences.coach_corrections
    if messages:
        query = select(Message).where(Message.conversation_id == c.id)
        if before:
            cursor = db.scalar(
                select(Message).where(
                    Message.id == before, Message.conversation_id == c.id
                )
            )
            if not cursor:
                raise HTTPException(404, "Message cursor not found.")
            query = query.where(
                (Message.created_at < cursor.created_at)
                | ((Message.created_at == cursor.created_at) & (Message.id < cursor.id))
            )
        rows = db.scalars(
            query.order_by(Message.created_at.desc(), Message.id.desc()).limit(101)
        ).all()
        view.has_more_messages = len(rows) > 100
        for m in reversed(rows[:100]):
            item = MessageView.model_validate(m)
            item.sources = sources_for_message(db, user, m.id)
            item.correction = visible_correction(user, c, m)
            view.messages.append(item)
    return view


def create(db, user, payload, scenario=None):
    level = user.preferences.current_level.upper()
    if scenario and scenario.cefr_level != level:
        raise HTTPException(422, "Choose a scenario at your saved level.")
    source = (
        source_for(db, user, payload.linked_lesson_id)
        if payload.linked_lesson_id
        else None
    )
    settings = get_settings()
    c = Conversation(
        user_id=user.id,
        title=scenario.title if scenario else payload.title,
        mode="roleplay" if scenario else payload.mode,
        cefr_level=level,
        scenario_id=scenario.id if scenario else None,
        linked_lesson_id=payload.linked_lesson_id,
        preview_mode=source.draft_preview if source else False,
        content_version_reference=source.content_version if source else None,
        model_provider=settings.ai_provider,
        model_name=settings.ollama_model,
    )
    db.add(c)
    if scenario:
        db.flush()
        db.add(Message(conversation_id=c.id, role="assistant", content=scenario.opening_french,
                       response_status="success", grounding_status="general_knowledge",
                       model_metadata={"authored_opening": True}))
    db.commit()
    db.refresh(c)
    return conversation_view(db, user, c)


def visible_correction(user, conversation, message):
    if conversation.scenario_id and user.preferences.coach_corrections == "after" and not conversation.completed_at:
        return None
    return message.model_metadata.get("correction")


def response_for(db, user, c, m):
    sources = sources_for_message(db, user, m.id)
    return ChatResponse(
        conversation_id=c.id,
        message_id=m.id,
        answer=m.content,
        cefr_level=c.cefr_level,
        grounding_status=m.grounding_status,
        sources=sources,
        suggested_actions=[{"label": s.title, "url": s.url} for s in sources],
        model={"provider": "authored" if m.model_name == "authored-practice" else "ollama", "model_name": m.model_name},
        correction=visible_correction(user, c, m),
    )


def validate_voice_style(answer, level):
    """Do not persist or synthesize an internal explanation as voice dialogue."""
    import re

    if re.search(
        r"\b(?:your|learner|user|stored|saved|registered)\s+(?:profile|personal (?:data|information))\b"
        r"|\b(?:votre|ton|vos|tes)\s+(?:profil|données personnelles|informations personnelles)\b"
        r"|\b(?:system instructions?|system prompts?|hidden instructions?|retrieval|metadata|first_name|general model knowledge)\b"
        r"|\b(?:instructions? système|métadonnées|contexte interne|profil utilisateur)\b",
        answer, re.I,
    ):
        raise ProviderUnavailable("Internal explanation in voice reply")
    french, _, english = answer.partition("\nEnglish:")
    if answer.count("?") > 1 or (level == "A1" and len(french.split()) > 35):
        raise ProviderUnavailable("Voice reply is not conversational")
    if english and ("\n" in english.strip() or len(english.split()) > 35):
        raise ProviderUnavailable("Voice explanation is too long")


def validate_answer(result, mode, question, level, sources, *, voice_practice=False):
    answer = result.text.strip()
    if not answer or len(answer) > 12000:
        raise ProviderUnavailable("Invalid response length")
    if voice_practice:
        validate_voice_style(answer, level)
    lowered = answer.casefold()
    if any(
        marker in lowered
        for marker in (
            "fluentloop_internal_policy",
            "you are the fluentloop french tutor",
            "<|system",
            "[inst]",
            "supporting data only:",
            "untrusted_curriculum",
            "learner identity data only:",
        )
    ):
        raise ProviderUnavailable("Internal prompt detected")
    # Citations/links are rendered only by the application. Reject model-supplied
    # resource identifiers, URLs and bracket citations rather than trusting them.
    import re

    if re.search(
        r"https?://|/lessons/|\[[^\]]{1,80}\]\(|\[(?:source\s*)?\d+\]|[0-9a-f]{8}-[0-9a-f-]{27,}",
        answer,
        re.I,
    ):
        raise ProviderUnavailable("Untrusted source reference")
    correction = None
    if mode == "correction":
        try:
            correction = Correction.model_validate_json(answer)
            if correction.original_text != question or correction.level != level:
                raise ValueError("Correction mismatch")
            if not correction.has_errors and correction.corrected_text != question:
                raise ValueError("Stylistic changes must be alternatives")
            if (
                sum(
                    len(x)
                    for x in correction.explanations
                    + correction.alternative_expressions
                )
                > 5000
            ):
                raise ValueError("Feedback too long")
            answer = (
                "Corrected: "
                + correction.corrected_text
                + "\n\n"
                + "\n".join(correction.explanations)
            )
        except (ValidationError, ValueError):
            raise ProviderUnavailable("Invalid correction") from None
    return answer, correction


def send(db, user, conversation_id, payload, provider, *, voice_practice=False):
    settings = get_settings()
    if len(payload.message) > settings.ai_max_input_characters:
        raise HTTPException(422, "Message is too long.")
    c = owned(db, user, conversation_id)
    previous = db.scalar(
        select(Message).where(
            Message.conversation_id == c.id,
            Message.request_id == payload.request_id,
            Message.role == "user",
        )
    )
    if previous and previous.content != payload.message:
        raise HTTPException(409, "Request ID already belongs to another message.")
    completed = db.scalar(
        select(Message).where(
            Message.conversation_id == c.id,
            Message.request_id == payload.request_id,
            Message.role == "assistant",
        )
    )
    if completed:
        return response_for(db, user, c, completed)
    if c.status != "active":
        raise HTTPException(409, "This conversation is closed.")
    if (
        db.scalar(select(func.count(Message.id)).where(Message.conversation_id == c.id))
        or 0
    ) >= 1000:
        raise HTTPException(
            409, "Conversation limit reached. Start a new conversation."
        )
    now = utcnow()
    lease = uuid4()
    cutoff = now - timedelta(seconds=settings.ai_request_timeout_seconds + 30)
    claimed = db.execute(
        update(Conversation)
        .where(
            Conversation.id == c.id,
            Conversation.status == "active",
            or_(
                Conversation.active_request_id.is_(None),
                Conversation.generation_started_at < cutoff,
            ),
        )
        .values(active_request_id=lease, generation_started_at=now)
        .execution_options(synchronize_session="fetch")
    ).rowcount
    if not claimed:
        db.rollback()
        raise HTTPException(
            409,
            "A response is already being generated. Retry with the same request ID.",
        )
    # Another worker may have completed between our initial read and lease claim.
    completed = db.scalar(
        select(Message).where(
            Message.conversation_id == c.id,
            Message.request_id == payload.request_id,
            Message.role == "assistant",
        )
    )
    if completed:
        c.active_request_id = None
        c.generation_started_at = None
        db.commit()
        return response_for(db, user, c, completed)
    previous = db.scalar(
        select(Message)
        .where(
            Message.conversation_id == c.id,
            Message.request_id == payload.request_id,
            Message.role == "user",
        )
        .execution_options(populate_existing=True)
    )
    if previous and previous.content != payload.message:
        c.active_request_id = None
        c.generation_started_at = None
        db.commit()
        raise HTTPException(409, "Request ID already belongs to another message.")
    # Recover abandoned pending turns; never send them as completed history.
    db.execute(
        update(Message)
        .where(Message.conversation_id == c.id, Message.response_status == "pending")
        .values(response_status="failed")
    )
    if previous:
        previous.response_status = "pending"
    else:
        previous = Message(
            conversation_id=c.id,
            role="user",
            content=payload.message,
            request_id=payload.request_id,
        )
        db.add(previous)
    db.commit()  # acceptance is durable, and the conversation lease is now visible
    cid = c.id
    uid = user.id
    try:
        c = owned(db, user, cid)
        context = retrieve(db, user, c.cefr_level, payload.message, c.linked_lesson_id)
        if any(s["source"]["draft_preview"] for s in context):
            c.preview_mode = True
        history = list(
            reversed(
                db.scalars(
                    select(Message)
                    .where(
                        Message.conversation_id == cid,
                        Message.response_status == "success",
                    )
                    .order_by(Message.created_at.desc(), Message.id.desc())
                    .limit(12)
                ).all()
            )
        )
        scenario = scenario_by_id(c.scenario_id)
        mode = c.mode
        level = c.cefr_level
        coach_context = evidence(db, user, level, cid)
        coach_context["recent_session_corrections"] = sum(
            bool((message.model_metadata.get("correction") or {}).get("has_errors"))
            for message in history if message.role == "assistant"
        )
        prompts = build_messages(
            level,
            mode,
            payload.message,
            history,
            context,
            scenario.model_dump() if scenario else None,
            user.preferences.explanation_language,
            learner_first_name=None if scenario else first_name_hint(
                user.profile.display_name if user.profile else None
            ),
            voice_practice=voice_practice,
            coach=(c.coach_difficulty, user.preferences.coach_corrections, coach_context),
        )
        db.commit()  # release read transaction BEFORE inference
        authored = LANGUAGE_ONLY_TURNS.get(c.scenario_id)
        if authored:
            position = sum(message.role == "user" for message in history)
            safe_reply = ScenarioReply(reply=authored[min(position, len(authored) - 1)])
            result = Generation(safe_reply.model_dump_json(), "authored-practice")
        else:
            result = provider.generate(
                prompts,
                structured=(ScenarioReply.model_json_schema() if scenario else
                            Correction.model_json_schema() if mode == "correction" else None),
            )
        scenario_correction = None
        if scenario:
            try:
                roleplay = ScenarioReply.model_validate_json(result.text)
            except ValidationError:
                raise ProviderUnavailable("Invalid roleplay response") from None
            result = Generation(roleplay.reply, result.model, result.metadata)
            suggestion = roleplay.correction
            if suggestion and suggestion.original_text == payload.message and suggestion.level == level:
                try:
                    safe_parts = [suggestion.corrected_text, *suggestion.explanations, *suggestion.alternative_expressions]
                    validate_answer(Generation("\n".join(safe_parts), result.model), "tutor", "", level, [])
                    if suggestion.has_errors and suggestion.corrected_text != payload.message and suggestion.explanations:
                        scenario_correction = suggestion.model_copy(update={"model_notes": ""})
                    elif not suggestion.has_errors and suggestion.corrected_text == payload.message and suggestion.alternative_expressions:
                        scenario_correction = suggestion.model_copy(update={"model_notes": ""})
                except ProviderUnavailable:
                    pass
        answer, correction = validate_answer(
            result, mode, payload.message, level, context, voice_practice=voice_practice
        )
        # Re-check current ownership, publication and role after the external call.
        db.expire_all()
        user = db.get(User, uid)
        if not user or not user.is_active:
            raise HTTPException(401, "Authentication required.")
        c = owned(db, user, cid)
        if c.active_request_id != lease:
            raise HTTPException(
                409, "Generation was superseded. Reload the conversation."
            )
        if c.status != "active":
            raise HTTPException(409, "Conversation archived during generation.")
        for item in context:
            source = source_for(db, user, UUID(item["source"]["lesson_id"]))
            if source.content_version != item["source"]["content_version"]:
                raise HTTPException(409, "Source content changed. Retry the message.")
        grounding = (
            "draft_preview"
            if any(s["source"]["draft_preview"] for s in context)
            else "curriculum_context" if context else "general_knowledge"
        )
        metadata = {
            k: v
            for k, v in result.metadata.items()
            if k in {"prompt_eval_count", "eval_count", "total_duration"}
            and isinstance(v, int)
        }
        if correction:
            metadata["correction"] = correction.model_dump()
        elif scenario_correction:
            metadata["correction"] = scenario_correction.model_dump()
        assistant = Message(
            conversation_id=cid,
            role="assistant",
            content=answer,
            request_id=payload.request_id,
            response_status="success",
            grounding_status=grounding,
            model_name=result.model,
            model_metadata=metadata,
        )
        db.add(assistant)
        db.flush()
        for item in context:
            ref = item["source"]
            db.add(
                MessageSource(
                    message_id=assistant.id,
                    source_record_id=UUID(ref["lesson_id"]),
                    content_version=ref["content_version"],
                    retrieval_score=item["score"],
                )
            )
        if correction:
            db.add(
                PracticeFeedback(
                    conversation_id=cid,
                    message_id=assistant.id,
                    user_id=uid,
                    cefr_level=level,
                    topic="Sentence correction",
                    feedback_type="correction",
                    corrected_text=correction.corrected_text,
                    explanation="\n".join(correction.explanations),
                )
            )
        previous = db.scalar(
            select(Message).where(
                Message.conversation_id == cid,
                Message.request_id == payload.request_id,
                Message.role == "user",
            )
        )
        previous.response_status = "success"
        c.active_request_id = None
        c.generation_started_at = None
        c.updated_at = utcnow()
        c.last_message_at = c.updated_at
        c.model_name = result.model
        db.commit()
        return response_for(db, user, c, assistant)
    except Exception as exc:
        db.rollback()
        # A stale worker cannot clear a newer worker's lease or mark its turn failed.
        released = db.execute(
            update(Conversation)
            .where(Conversation.id == cid, Conversation.active_request_id == lease)
            .values(active_request_id=None, generation_started_at=None)
        ).rowcount
        if released:
            db.execute(
                update(Message)
                .where(
                    Message.conversation_id == cid,
                    Message.request_id == payload.request_id,
                    Message.role == "user",
                    Message.response_status == "pending",
                )
                .values(response_status="failed")
            )
        db.commit()
        if isinstance(exc, HTTPException):
            raise
        logger.warning(
            "ai_generation_failed", extra={"failure_type": type(exc).__name__}
        )
        raise HTTPException(
            503,
            "The tutor is unavailable or returned an invalid response. Retry with the same request ID.",
        ) from None
