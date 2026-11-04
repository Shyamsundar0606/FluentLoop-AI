"""Container sniffing before any native decoder. Extensions are not trusted."""

from fastapi import HTTPException
from app.config import get_settings


def validate_upload(data: bytes) -> str:
    if not data:
        raise HTTPException(422, "Recording is empty.")
    if len(data) > get_settings().speech_max_upload_bytes:
        raise HTTPException(413, "Recording exceeds the upload limit.")
    if data.startswith(b"\x1aE\xdf\xa3"):
        return "webm"
    if data.startswith(b"OggS"):
        return "ogg"
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "wav"
    if len(data) > 12 and data[4:8] == b"ftyp":
        return "mp4"
    raise HTTPException(415, "Use WebM/Opus, Ogg/Opus, PCM WAV or MP4/AAC audio.")
