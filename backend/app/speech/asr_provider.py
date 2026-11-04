from typing import Protocol
from app.speech.schemas import Transcription


class SpeechUnavailable(Exception):
    pass


class ASRProvider(Protocol):
    def transcribe(self, audio: bytes) -> Transcription: ...


class TTSProvider(Protocol):
    def synthesize(self, text: str) -> bytes: ...
