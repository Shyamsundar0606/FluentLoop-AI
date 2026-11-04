"""Guarded deterministic speech test API, never used by production startup."""

from pathlib import Path
import sys
from scripts.ai_e2e_server import app
from app.config import get_settings
from sqlalchemy.engine import make_url

assert make_url(get_settings().database_url).database.startswith("fluentloop_m06_")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_speech import FakeSpeech, FakeTutor
from app.speech.providers import get_speech_provider
from app.api.v1.ai import provider_dependency

original_tutor = app.dependency_overrides[provider_dependency]()


class BrowserTutor(FakeTutor):
    def generate(self, messages, **kwargs):
        if "Voice practice:" in messages[0]["content"]:
            return super().generate(messages, **kwargs)
        return original_tutor.generate(messages, **kwargs)


class BrowserSpeech(FakeSpeech):
    def transcribe(self, data):
        if data.startswith(b"OggS"):
            from app.speech.schemas import Transcription
            return Transcription(status="uncertain", language="fr",
                text="Bonjour, Zamapel, Xiaomi, Zabite, Paris.",
                duration_ms=5200, model="deterministic-browser-test")
        return super().transcribe(data)


speech = BrowserSpeech()
tutor = BrowserTutor()
app.dependency_overrides[get_speech_provider] = lambda: speech
app.dependency_overrides[provider_dependency] = lambda: tutor
