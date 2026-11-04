from datetime import timedelta, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import hashlib
import os
import wave
from fastapi import HTTPException
from sqlalchemy import select
from app.config import get_settings
from app.models import utcnow
from app.speech.models import AudioAsset
from app.ai.retrieval import source_for
from app.ai import orchestrator as ai


def path_for(key):
    root = Path(get_settings().speech_storage_path).resolve()
    path = (root / key).resolve()
    if path.parent != root or len(key) > 80:
        raise HTTPException(404, "Audio not found.")
    return path


def expired(asset):
    timestamp = asset.retention_expires_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp <= utcnow()


def store(db, user, data, *, session=None, lesson=None, source="tutor", duration=None,codec=None):
    if len(data) > 6_000_000:
        raise HTTPException(422, "Audio output exceeds limit.")
    if source == "tutor" or source == "reference":
        try:
            with wave.open(BytesIO(data), "rb") as wav:
                if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                    raise ValueError()
                duration = round(wav.getnframes() / wav.getframerate() * 1000)
                if duration > 120000:
                    raise ValueError()
        except (wave.Error, ValueError, ZeroDivisionError):
            raise HTTPException(503, "Invalid synthesized audio.") from None
        media = "audio/wav"
        codec = "pcm_s16le"
    else:
        from app.speech.audio_validation import validate_upload

        container = validate_upload(data)
        media = {
            "webm": "audio/webm",
            "ogg": "audio/ogg",
            "wav": "audio/wav",
            "mp4": "audio/mp4",
        }[container]
        codec = codec or "unknown"
    key = uuid4().hex + ".audio"
    path = path_for(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(data)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    asset = AudioAsset(
        owner_user_id=user.id,
        speech_session_id=session.id if session else None,
        lesson_id=lesson.lesson_id if lesson else None,
        content_version=lesson.content_version if lesson else None,
        storage_key=key,
        media_type=media,
        codec=codec,
        duration_ms=duration,
        byte_size=len(data),
        checksum=hashlib.sha256(data).hexdigest(),
        source_type=source,
        retention_expires_at=utcnow()
        + timedelta(hours=get_settings().speech_audio_retention_hours),
    )
    db.add(asset)
    return asset


def owned_audio(db, user, asset_id, *, allow_deleted=False):
    asset = db.scalar(
        select(AudioAsset).where(
            AudioAsset.id == asset_id, AudioAsset.owner_user_id == user.id
        )
    )
    if not asset:
        raise HTTPException(404, "Audio not found.")
    if asset.speech_session_id:
        from app.speech.models import SpeechSession

        session = db.get(SpeechSession, asset.speech_session_id)
        if session.user_id != user.id:
            raise HTTPException(404, "Audio not found.")
        ai.owned(db, user, session.ai_conversation_id)
    if asset.lesson_id:
        source = source_for(db, user, asset.lesson_id)
        if source.content_version != asset.content_version:
            raise HTTPException(404, "Audio no longer available.")
    if not allow_deleted and (asset.deleted_at or expired(asset)):
        raise HTTPException(404, "Audio expired or deleted.")
    return asset


def delete(db, asset):
    path_for(asset.storage_key).unlink(missing_ok=True)
    asset.deleted_at = utcnow()


def cleanup(db):
    rows = db.scalars(
        select(AudioAsset)
        .where(
            AudioAsset.deleted_at.is_(None), AudioAsset.retention_expires_at <= utcnow()
        )
        .limit(100)
    ).all()
    for asset in rows:
        delete(db, asset)
    db.commit()
    # Failed commits can leave an orphan; expire only controlled files after TTL.
    import itertools, time

    root = Path(get_settings().speech_storage_path).resolve()
    cutoff = time.time() - get_settings().speech_audio_retention_hours * 3600
    for path in itertools.islice(root.glob("*.audio"), 100):
        if path.stat().st_mtime < cutoff and not db.scalar(
            select(AudioAsset.id).where(AudioAsset.storage_key == path.name)
        ):
            path.unlink(missing_ok=True)
    return len(rows)
