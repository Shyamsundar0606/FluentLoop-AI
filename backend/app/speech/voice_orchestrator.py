import hashlib
from datetime import timedelta
from uuid import uuid4
from io import BytesIO
import wave
from fastapi import HTTPException
from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError
from app.config import get_settings
from app.models import User, utcnow
from app.ai import orchestrator as ai
from app.ai.models import Conversation, Message
from app.ai.response_schemas import CreateConversation, SendMessage
from app.ai.scenarios import scenario_by_id
from app.speech.models import (
    SpeechSession,
    SpeechTurn,
    AudioAsset,
    PronunciationAttempt,
    SpeechProgress,
)
from app.speech.schemas import (
    SpeechSessionView,
    TurnView,
    AudioView,
    Transcription,
    AttemptView,
)
from app.speech import storage, pronunciation_service as pronunciation
from app.speech.asr_provider import SpeechUnavailable
from app.speech.audio_validation import validate_upload


def owned(db, user, sid):
    if not user or not user.is_active:
        raise HTTPException(401, "Authentication required.")
    session = db.scalar(
        select(SpeechSession).where(
            SpeechSession.id == sid, SpeechSession.user_id == user.id
        )
    )
    if not session:
        raise HTTPException(404, "Speech session not found.")
    c = ai.owned(db, user, session.ai_conversation_id)
    return session, c


def start(db, user, payload):
    if payload.level and payload.level != user.preferences.current_level.upper():
        raise HTTPException(
            422,
            "Choose your saved French level, or explicitly update it in Settings first.",
        )
    if payload.conversation_id and payload.scenario_id:
        raise HTTPException(422, "Choose an existing conversation or a scenario.")
    if payload.conversation_id:
        c = ai.owned(db, user, payload.conversation_id)
        if c.status != "active":
            raise HTTPException(409, "Conversation is archived.")
        existing = db.scalar(
            select(SpeechSession).where(SpeechSession.ai_conversation_id == c.id)
        )
        if existing:
            return view(db, user, existing)
    else:
        scenario = scenario_by_id(payload.scenario_id) if payload.scenario_id else None
        if payload.scenario_id and not scenario:
            raise HTTPException(404, "Scenario not found.")
        created = ai.create(
            db,
            user,
            CreateConversation(mode="roleplay", title="French voice practice"),
            scenario,
        )
        c = db.get(Conversation, created.id)
    session = SpeechSession(
        user_id=user.id,
        ai_conversation_id=c.id,
        cefr_level=c.cefr_level,
        scenario_id=c.scenario_id,
    )
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Speech session already exists. Refresh history."
        ) from None
    return view(db, user, session)


def audio_view(db, user, asset_id, spoken_text=None):
    if not asset_id:
        return AudioView(status="unavailable", spoken_text=spoken_text)
    try:
        asset = storage.owned_audio(db, user, asset_id)
        if not storage.path_for(asset.storage_key).is_file():
            return AudioView(status='unavailable',spoken_text=spoken_text)
        return AudioView(
            status="ready",
            asset_id=asset.id,
            spoken_text=spoken_text,
            voice=get_settings().speech_tts_voice,
            duration_ms=asset.duration_ms,
        )
    except HTTPException as exc:
        if exc.status_code != 404:
            raise
        return AudioView(status="unavailable", spoken_text=spoken_text)


def turn_view(db, user, session, turn):
    review = turn.transcription_metadata.get("review")
    if review:
        # Legacy confirmations already preserve both strings. Derive their flag
        # on read without rewriting history or inventing a new confirmation.
        review = {**review, "edited": review.get("edited", review["original_text"] != review["confirmed_text"])}
    tutor = None
    if turn.ai_message_id:
        msg = db.get(Message, turn.ai_message_id)
        if msg and msg.conversation_id == session.ai_conversation_id:
            tutor = ai.response_for(
                db, user, db.get(Conversation, session.ai_conversation_id), msg
            )
    return TurnView(
        id=turn.id,
        request_id=turn.request_id,
        transcript=turn.transcript,
        transcription_status=turn.transcription_status,
        transcription=turn.transcription_metadata.get("result"),
        review=review,
        tutor=tutor,
        tutor_audio=audio_view(db, user, turn.tutor_audio_asset_id, turn.spoken_text),
        input_audio_id=(
            turn.audio_asset_id
            if turn.audio_asset_id
            and audio_view(db, user, turn.audio_asset_id).status == "ready"
            else None
        ),
        status=turn.status,
        created_at=turn.created_at,
    )


def view(db, user, session, include_turns=False, offset=0):
    session, c = owned(db, user, session.id)
    rows = (
        list(
            reversed(
                db.scalars(
                    select(SpeechTurn)
                    .where(SpeechTurn.speech_session_id == session.id)
                    .order_by(SpeechTurn.created_at.desc())
                    .offset(offset)
                    .limit(101)
                ).all()
            )
        )
        if include_turns
        else []
    )
    return SpeechSessionView(
        id=session.id,
        conversation_id=c.id,
        cefr_level=session.cefr_level,
        scenario_id=session.scenario_id,
        status=session.status,
        title=c.title,
        draft_preview=c.preview_mode,
        created_at=session.created_at,
        last_activity_at=session.last_activity_at,
        turns=[turn_view(db, user, session, r) for r in rows[-100:]],
        has_more_turns=len(rows) > 100,
    )


def french_portion(text):
    import re
    text = text.split("\nEnglish:")[0].strip()
    text = ' '.join(re.split(r'(?<=[.!?])\s+',text)[:3])
    if not text or len(text) > 600:
        return None
    try:
        from langdetect import detect_langs, DetectorFactory

        DetectorFactory.seed = 0
        langs = detect_langs(text)
        return (
            text if langs and langs[0].lang == "fr" and langs[0].prob >= 0.7 else None
        )
    except Exception:
        return None


def submit(
    db,
    user,
    sid,
    request_id,
    speech,
    ai_provider,
    *,
    data=None,
    text=None,
    retain=False,
    reviewed_turn_id=None,
):
    session, c = owned(db, user, sid)
    if session.status != "active":
        raise HTTPException(409, "Speech session is complete.")
    if data is not None:
        validate_upload(data)
    review_source = None
    if reviewed_turn_id is not None:
        if not text or not text.strip():
            raise HTTPException(422, "Confirm a nonempty sentence.")
        review_source = db.scalar(select(SpeechTurn).where(
            SpeechTurn.id == reviewed_turn_id,
            SpeechTurn.speech_session_id == sid,
            SpeechTurn.user_id == user.id,
        ))
        if not review_source:
            raise HTTPException(404, "Original speech turn not found.")
        if (data is not None or review_source.transcription_status != "uncertain"
                or review_source.status != "unusable" or not review_source.transcript.strip()):
            raise HTTPException(422, "Only an uncertain recognized utterance can be reviewed.")
    # Include provenance in idempotency: a text retry must not silently change
    # which original recording the learner confirmed. Legacy text hashes stay valid.
    digest_input = data if data is not None else text.encode()
    if reviewed_turn_id is not None:
        digest_input = str(reviewed_turn_id).encode() + b"\0" + digest_input
    digest = hashlib.sha256(digest_input).hexdigest()
    turn = db.scalar(
        select(SpeechTurn).where(
            SpeechTurn.speech_session_id == sid, SpeechTurn.request_id == request_id
        )
    )
    if turn and turn.input_checksum != digest:
        raise HTTPException(409, "Request ID belongs to different input.")
    if turn and turn.status in {"success", "unusable"}:
        return turn_view(db, user, session, turn)
    lease = uuid4()
    now = utcnow()
    timeout = (
        get_settings().speech_processing_timeout_seconds * 3
        + get_settings().ai_request_timeout_seconds
        + 40
    )
    claimed = db.execute(
        update(SpeechSession)
        .where(
            SpeechSession.id == sid,
            SpeechSession.status == "active",
            or_(
                SpeechSession.active_request_id.is_(None),
                SpeechSession.processing_started_at < now - timedelta(seconds=timeout),
            ),
        )
        .values(active_request_id=lease, processing_started_at=now)
        .execution_options(synchronize_session="fetch")
    ).rowcount
    if not claimed:
        db.rollback()
        raise HTTPException(
            409, "Another speech turn is processing. Retry the same request ID later."
        )
    turn = db.scalar(
        select(SpeechTurn)
        .where(SpeechTurn.speech_session_id == sid, SpeechTurn.request_id == request_id)
        .execution_options(populate_existing=True)
    )
    if turn and turn.input_checksum != digest:
        db.rollback()
        raise HTTPException(409, "Request ID belongs to different input.")
    if turn and turn.status in {"success", "unusable"}:
        session.active_request_id = None
        session.processing_started_at = None
        db.commit()
        return turn_view(db, user, session, turn)
    if not turn:
        turn = SpeechTurn(
            speech_session_id=sid,
            user_id=user.id,
            request_id=request_id,
            input_checksum=digest,
        )
        db.add(turn)
    turn.status = "pending"
    db.commit()
    tid = turn.id
    uid = user.id
    try:
        if not turn.transcript:
            if data is not None:
                db.commit()  # no transaction during ASR
                result = speech.transcribe(data)
                db.expire_all()
                user = db.get(User, uid)
                session, c = owned(db, user, sid)
                turn = db.get(SpeechTurn, tid)
                if session.active_request_id != lease:
                    raise HTTPException(409, "Speech turn was superseded.")
                turn.transcription_metadata = {"result": result.model_dump()}
                turn.transcription_status = result.status
                turn.asr_model = result.model
                turn.language = result.language
                turn.transcript = result.text
                if retain:
                    asset = storage.store(
                        db,
                        user,
                        data,
                        session=session,
                        source="learner",
                        duration=result.duration_ms,
                        codec=result.codec,
                    )
                    db.flush()
                    turn.audio_asset_id = asset.id
                if result.status != "transcribed" or not result.text.strip():
                    turn.status = "unusable"
                    session.active_request_id = None
                    session.processing_started_at = None
                    session.last_activity_at = utcnow()
                    db.commit()
                    return turn_view(db, user, session, turn)
            else:
                turn.transcript = text
                turn.transcription_status = "user_confirmed" if review_source else "text_fallback"
                turn.language = "fr"
                if review_source:
                    # Existing JSON storage is sufficient. Never overwrite the
                    # source ASR result or label learner editing as recognition.
                    turn.transcription_metadata = {"review": {
                        "source_turn_id": str(review_source.id),
                        "original_text": review_source.transcript,
                        "confirmed_text": text,
                        "confirmed_at": utcnow().isoformat(),
                        "edited": text != review_source.transcript,
                    }}
            db.commit()
        session, c = owned(db, user, sid)
        turn = db.get(SpeechTurn, tid)
        if not turn.ai_message_id:
            response = ai.send(
                db,
                user,
                c.id,
                SendMessage(message=turn.transcript, request_id=request_id),
                ai_provider,
                voice_practice=True,
            )
            turn = db.get(SpeechTurn, tid)
            turn.ai_message_id = response.message_id
            turn.spoken_text = french_portion(response.answer)
            db.commit()
        # Failure here never regenerates the tutor answer; explicit audio retry is separate.
        if turn.spoken_text and not turn.tutor_audio_asset_id:
            spoken = turn.spoken_text
            db.commit()
            try:
                wav = speech.synthesize(spoken)
                db.expire_all()
                user = db.get(User, uid)
                session, c = owned(db, user, sid)
                turn = db.get(SpeechTurn, tid)
                if session.active_request_id != lease:
                    raise HTTPException(409, "Speech turn was superseded.")
                asset = storage.store(db, user, wav, session=session)
                db.flush()
                turn.tutor_audio_asset_id = asset.id
            except SpeechUnavailable:
                pass
            except HTTPException as exc:
                if exc.status_code != 503:
                    raise
                # Invalid synthesized bytes are an audio-only failure too.
        session, c = owned(db, user, sid)
        turn = db.get(SpeechTurn, tid)
        if session.active_request_id != lease:
            raise HTTPException(409, "Speech turn was superseded.")
        turn.status = "success"
        session.active_request_id = None
        session.processing_started_at = None
        session.last_activity_at = utcnow()
        session.updated_at = utcnow()
        db.commit()
        return turn_view(db, user, session, turn)
    except Exception as exc:
        db.rollback()
        released = db.execute(
            update(SpeechSession)
            .where(SpeechSession.id == sid, SpeechSession.active_request_id == lease)
            .values(active_request_id=None, processing_started_at=None)
        ).rowcount
        if released:
            db.execute(
                update(SpeechTurn).where(SpeechTurn.id == tid).values(status="failed")
            )
        db.commit()
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(
            503,
            "Speech processing is unavailable. Retry with the same request ID; text tutoring remains available.",
        ) from None


def retry_audio(db, user, sid, tid, speech):
    session, c = owned(db, user, sid)
    turn = db.scalar(
        select(SpeechTurn).where(
            SpeechTurn.id == tid,
            SpeechTurn.speech_session_id == sid,
            SpeechTurn.user_id == user.id,
        )
    )
    if not turn or not turn.spoken_text:
        raise HTTPException(404, "No French speech text available for this turn.")
    if audio_view(db, user, turn.tutor_audio_asset_id).status == "ready":
        return turn_view(db, user, session, turn)
    spoken = turn.spoken_text
    uid = user.id
    db.commit()
    wav = speech.synthesize(spoken)
    db.expire_all()
    user = db.get(User, uid)
    session, c = owned(db, user, sid)
    turn = db.scalar(select(SpeechTurn).where(SpeechTurn.id == tid).with_for_update())
    if audio_view(db, user, turn.tutor_audio_asset_id).status != "ready":
        asset = storage.store(db, user, wav, session=session)
        db.flush()
        turn.tutor_audio_asset_id = asset.id
        db.commit()
    return turn_view(db, user, session, turn)


def attempt_view(db, user, attempt):
    target = pronunciation.target(db, user, attempt.target_id)
    if target.content_version != attempt.content_version:
        raise HTTPException(404, "Target version changed.")
    feedback = attempt.feedback_metadata
    return AttemptView(
        id=attempt.id,
        request_id=attempt.request_id,
        target=target,
        recognized_text=attempt.recognized_text,
        recognition_match=attempt.recognition_match,
        recognition_feedback=feedback["recognition_feedback"],
        assessment_status=attempt.assessment_status,
        limitations=pronunciation.LIMITATIONS,
        transcription=feedback["transcription"],
        created_at=attempt.created_at,
        input_audio_id=(
            attempt.audio_asset_id
            if attempt.audio_asset_id
            and audio_view(db, user, attempt.audio_asset_id).status == "ready"
            else None
        ),
    )


def attempt(db, user, target_id, rid, data, retain, speech):
    validate_upload(data)
    target = pronunciation.target(db, user, target_id)
    digest = hashlib.sha256(data).hexdigest()
    old = db.scalar(
        select(PronunciationAttempt).where(
            PronunciationAttempt.user_id == user.id,
            PronunciationAttempt.request_id == rid,
        )
    )
    if old:
        if old.input_checksum != digest or old.target_id != target_id:
            raise HTTPException(409, "Request ID belongs to another attempt.")
        return attempt_view(db, user, old)
    uid = user.id
    version = target.content_version
    db.commit()
    result = speech.transcribe(data)
    db.expire_all()
    user = db.get(User, uid)
    if not user or not user.is_active:
        raise HTTPException(401, "Authentication required.")
    target = pronunciation.target(db, user, target_id)
    if version != target.content_version:
        raise HTTPException(409, "Target changed. Start a new attempt.")
    # Serialize persistence per owner; model inference remains outside transactions.
    db.scalar(select(User).where(User.id == uid).with_for_update())
    old = db.scalar(
        select(PronunciationAttempt).where(
            PronunciationAttempt.user_id == uid, PronunciationAttempt.request_id == rid
        )
    )
    if old:
        if old.input_checksum != digest or old.target_id != target_id:
            raise HTTPException(409, "Request ID belongs to another attempt.")
        return attempt_view(db, user, old)
    feedback = pronunciation.assess(target.text, result)
    item = PronunciationAttempt(
        user_id=uid,
        request_id=rid,
        input_checksum=digest,
        target_id=target_id,
        target_text=target.text,
        lesson_id=target.lesson_id,
        content_version=version,
        target_level=target.level,
        recognized_text=result.text,
        recognition_match=feedback["recognition_match"],
        assessment_status=feedback["assessment_status"],
        feedback_metadata={**feedback, "transcription": result.model_dump()},
    )
    if retain:
        asset = storage.store(
            db, user, data, lesson=target, source="learner", duration=result.duration_ms,codec=result.codec
        )
        db.flush()
        item.audio_asset_id = asset.id
    db.add(item)
    progress = db.scalar(
        select(SpeechProgress).where(
            SpeechProgress.user_id == uid, SpeechProgress.target_id == target_id
        )
    )
    if not progress:
        progress = SpeechProgress(
            user_id=uid,
            target_id=target_id,
            lesson_id=target.lesson_id,
            content_version=version,
            cefr_level=target.level,
            attempt_count=0,
        )
        db.add(progress)
    progress.attempt_count += 1
    progress.last_practiced_at = utcnow()
    progress.updated_at = utcnow()
    progress.latest_assessment_status = feedback["assessment_status"]
    db.commit()
    return attempt_view(db, user, item)
