from functools import lru_cache
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from app.config import get_settings
from app.speech.schemas import Transcription
from app.speech.asr_provider import SpeechUnavailable


class RemoteSpeech:
    def __init__(self):
        s = get_settings()
        url = urlsplit(s.speech_worker_url)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
        ):
            raise SpeechUnavailable()
        self.client = httpx.Client(
            base_url=s.speech_worker_url,
            headers={"X-Speech-Key": s.speech_worker_token},
            timeout=httpx.Timeout(s.speech_processing_timeout_seconds + 10, connect=3),
            limits=httpx.Limits(max_connections=4, max_keepalive_connections=2),
            trust_env=False,
            follow_redirects=False,
        )

    def health(self):
        try:
            r = self.client.get("/health", timeout=3)
            r.raise_for_status()
            return r.json()
        except Exception:
            return {"asr": False, "tts": False}

    def transcribe(self, audio):
        try:
            r = self.client.post(
                "/transcribe",
                content=audio,
                headers={"Content-Type": "application/octet-stream"},
            )
            if r.status_code == 422:
                raise HTTPException(
                    422,
                    "Recording could not be decoded. Use a short supported audio recording.",
                )
            r.raise_for_status()
            result=Transcription.model_validate(r.json())
            if result.duration_ms>get_settings().speech_max_duration_seconds*1000:
                raise HTTPException(422,'Recording exceeds configured duration limit.')
            return result
        except HTTPException:
            raise
        except Exception:
            raise SpeechUnavailable() from None

    def synthesize(self, text):
        try:
            with self.client.stream(
                "POST", "/synthesize", json={"text": text, "language": "fr"}
            ) as r:
                r.raise_for_status()
                data = bytearray()
                for chunk in r.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 6_000_000:
                        raise SpeechUnavailable()
            return bytes(data)
        except Exception:
            raise SpeechUnavailable() from None


@lru_cache
def get_speech_provider():
    try:return RemoteSpeech()
    except SpeechUnavailable:raise HTTPException(503,'Speech service configuration is unavailable.') from None
