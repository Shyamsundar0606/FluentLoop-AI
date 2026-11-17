"""Allowlisted personal-data pages and transactional account erasure."""
import json
from datetime import timedelta
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select
from app.core.database import Base
from app.models import User, utcnow
from app.privacy_models import AccountErasureJob
from app.security import verify_password
from app.speech.models import AudioAsset
from app.speech.storage import path_for

EXPORTS = {
    "profile": ("user_profiles", "display_name,preferred_name,native_language,country,timezone,learning_goal,registration_age_band,created_at"),
    "preferences": ("user_preferences", "explanation_language,target_language,current_level,target_level,daily_study_minutes,learning_focus,theme,audio_playback_speed,motivation_enabled,coach_corrections"),
    "lesson_progress": ("lesson_progress", "id,lesson_id,cefr_level,status,first_started_at,last_studied_at,completed_at,best_score,latest_score,completion_count"),
    "assessments_and_lessons": ("learning_sessions", "id,lesson_id,lesson_content_version,cefr_level,status,activity_key,started_at,completed_at,current_exercise_position,total_exercises,score_points,max_score_points"),
    "answers": ("exercise_attempts", "id,learning_session_id,session_exercise_id,answer_payload,submitted_answer,is_correct,awarded_points,max_points,submitted_at"),
    "writing": ("writing_submissions", "id,lesson_id,cefr_level,lesson_content_version,original_text,feedback_status,created_at"),
    "learning_activity": ("learning_activity_events", "id,session_id,lesson_id,event_type,created_at"),
    "rewards": ("learning_rewards", "id,kind,source_id,activity_type,xp,earned_at,study_date,timezone"),
    "achievements": ("learning_achievements", "id,achievement_key,earned_at"),
    "conversations": ("ai_conversations", "id,title,mode,cefr_level,scenario_id,coach_difficulty,completed_at,status,created_at,updated_at"),
    "messages": ("ai_messages", "id,conversation_id,role,content,created_at,response_status"),
    "voice_conversations": ("speech_sessions", "id,ai_conversation_id,cefr_level,scenario_id,status,started_at,completed_at"),
    "voice_transcripts": ("speech_turns", "id,speech_session_id,transcript,spoken_text,language,transcription_status,status,created_at"),
}


def reauthenticate(user, password):
    if not verify_password(user.password_hash, password):
        raise HTTPException(403, "Password confirmation failed.")


def export_page(db, user, section, offset):
    if section not in EXPORTS:
        raise HTTPException(422, "Choose an available export section.")
    name, fields = EXPORTS[section]
    table = Base.metadata.tables[name]
    query = select(*(table.c[field] for field in fields.split(",")))
    if section == "messages":
        conversations = Base.metadata.tables["ai_conversations"]
        query = query.where(table.c.conversation_id.in_(select(conversations.c.id).where(
            conversations.c.user_id == user.id)))
    else:
        query = query.where(table.c.user_id == user.id)
    # Only explicit columns are exported. Snapshots, private keys, model metadata,
    # tokens, audio storage paths and other accounts never enter the projection.
    rows = db.execute(query.order_by(table.c.id).offset(offset).limit(101)).mappings().all()
    items = []
    size = 0
    for row in rows[:100]:
        item = jsonable_encoder(dict(row))
        encoded_size = len(json.dumps(item, ensure_ascii=False).encode())
        if size + encoded_size > 1_500_000:
            break
        items.append(item); size += encoded_size
    if rows and not items:
        raise HTTPException(413, "This record needs an operator-assisted export.")
    return dict(section=section, generated_at=utcnow(), account_email=user.email, items=items,
        next_offset=offset+len(items) if len(rows) > len(items) else None,
        notice="Personal data at request time. Curriculum snapshots/answer keys, authentication secrets and raw audio files are excluded.")


def erase(db, user):
    # Serialize with operations that lock the user, including reward synchronization.
    locked = db.scalar(select(User).where(User.id == user.id).with_for_update())
    if locked is None:
        raise HTTPException(404, "Account unavailable.")
    assets = db.scalars(select(AudioAsset.storage_key).where(AudioAsset.owner_user_id == user.id).limit(10001)).all()
    if len(assets) > 10000:
        raise HTTPException(413, "This account needs operator-assisted audio erasure.")
    for key in assets:
        path_for(key)  # Validate every private path before deleting any account data.
    job = AccountErasureJob(storage_keys=list(assets), account_reference=user.id)
    db.add(job); db.flush(); receipt = job.id
    # Delete dependent owned rows first, including composite owner foreign keys.
    # Child records without owner columns cascade from their owned parent.
    for table in reversed(Base.metadata.sorted_tables):
        owner = next((table.c[key] for key in ("user_id", "owner_user_id") if key in table.c), None)
        if owner is not None:
            db.execute(delete(table).where(owner == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()  # The outbox and all relational deletion succeed or roll back together.
    return receipt


def cleanup_erasure_jobs(db):
    # Backup policy must expire all recoverable copies within this 90-day window.
    # Pending jobs are never expired while private files still need erasure.
    db.execute(delete(AccountErasureJob).where(AccountErasureJob.completed_at < utcnow()-timedelta(days=90)))
    jobs = db.scalars(select(AccountErasureJob).where(AccountErasureJob.completed_at.is_(None))
        .order_by(AccountErasureJob.created_at).limit(20).with_for_update(skip_locked=True)).all()
    for job in jobs:
        try:
            for key in job.storage_keys[:100]:
                path_for(key).unlink(missing_ok=True)
        except (OSError, HTTPException):
            continue  # Persisted keys remain available for the next bounded cleanup pass.
        job.storage_keys = job.storage_keys[100:]
        if not job.storage_keys:
            job.completed_at = utcnow()
    db.commit()
