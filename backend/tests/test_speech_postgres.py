import os
import time
from pathlib import Path
from uuid import uuid4, UUID
from threading import Event
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db
from app.models import User
from app.config import Settings, get_settings
from app.services.email import get_email_service
from app.api.v1.ai import provider_dependency
from app.speech.providers import get_speech_provider, RemoteSpeech
from app.ai.providers.ollama_provider import OllamaProvider
from app.speech.models import SpeechTurn, PronunciationAttempt
from app.speech.schemas import Transcription
from test_speech import FakeSpeech, FakeTutor, start, upload, wav
from test_learning import _register_and_login, _csrf, _import_content, _set_role
from conftest import CapturedEmailService, IsolatedRateLimitRedis

URL = os.environ.get("SPEECH_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not URL,
    reason="Set SPEECH_TEST_DATABASE_URL to an isolated fluentloop_m06_* PostgreSQL database",
)


def test_speech_postgres_and_optional_live_pipeline(monkeypatch, tmp_path):
    assert make_url(URL).database.startswith("fluentloop_m06_")
    engine = create_engine(URL)
    sessions = sessionmaker(bind=engine, autoflush=False)

    def db_dependency():
        with sessions() as db:
            yield db

    email = CapturedEmailService()
    speech = FakeSpeech()
    tutor = FakeTutor()
    app.dependency_overrides[get_db] = db_dependency
    app.dependency_overrides[get_email_service] = lambda: email
    app.dependency_overrides[get_speech_provider] = lambda: speech
    app.dependency_overrides[provider_dependency] = lambda: tutor
    monkeypatch.setattr(
        "app.services.rate_limit.redis_client", IsolatedRateLimitRedis()
    )
    monkeypatch.setattr(get_settings(), "speech_storage_path", str(tmp_path))
    account = f"speech-{uuid4().hex[:10]}@example.com"
    try:
        with TestClient(app, headers={"Origin": "http://localhost:3000"}) as client:
            _register_and_login(client, email, account)
            sid = start(client)
            rid = str(uuid4())
            ready = Event()
            release = Event()

            def blocked():
                ready.set()
                assert release.wait(20)

            speech.callback = blocked
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(upload, client, sid, rid)
                assert ready.wait(10)
                try:
                    assert upload(client, sid).status_code == 409
                finally:
                    release.set()
                result = first.result(20)
                assert result.status_code == 200, result.text
            speech.callback = None
            assert upload(client, sid, rid).json()["id"] == result.json()["id"]
            with sessions() as db:
                assert (
                    db.scalar(
                        select(func.count(SpeechTurn.id)).where(
                            SpeechTurn.speech_session_id == UUID(sid)
                        )
                    )
                    == 1
                )
            _import_content(sessions)
            _set_role(sessions, account, "admin")
            preview = Settings(
                APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=True
            )
            monkeypatch.setattr(
                "app.services.draft_preview.get_settings", lambda: preview
            )
            target = client.get("/api/v1/speech/pronunciation/targets").json()[0]
            response = client.post(
                "/api/v1/speech/pronunciation/attempts",
                data={"target_id": target["id"], "request_id": str(uuid4())},
                files={"audio": ("test.wav", wav())},
                headers=_csrf(client),
            )
            assert response.status_code == 200, response.text
            assert response.json()["acoustic_score"] is None
            with sessions() as db:
                assert (
                    db.scalar(
                        select(func.count(PronunciationAttempt.id)).where(
                            PronunciationAttempt.user_id
                            == db.scalar(select(User.id).where(User.email == account))
                        )
                    )
                    == 1
                )
            # Review provenance is stored in real PostgreSQL, not just the
            # SQLite unit-test database. ASR is explicitly injected for this stage.
            original_transcribe = speech.transcribe
            speech.transcribe = lambda data: Transcription(status="uncertain", language="fr",
                text="Bonjour, Zamapel, Xiaomi, Zabite, Paris.", duration_ms=5000, model="fake-asr")
            source = upload(client, sid).json()
            review_payload = dict(message="Bonjour, je m'appelle Camille. J'habite à Paris.",
                reviewed_turn_id=source["id"], request_id=str(uuid4()))
            confirmed = client.post(f"/api/v1/speech/sessions/{sid}/text", json=review_payload, headers=_csrf(client))
            assert confirmed.status_code == 200, confirmed.text
            with sessions() as db:
                saved = db.get(SpeechTurn, UUID(confirmed.json()["id"]))
                assert saved.transcription_metadata["review"]["source_turn_id"] == source["id"]
                assert saved.transcription_metadata["review"]["edited"] is True
                assert db.get(SpeechTurn, UUID(source["id"])).transcript.startswith("Bonjour, Zamapel")
            speech.transcribe = original_transcribe
            if os.getenv("SPEECH_LIVE") == "1":
                monkeypatch.setattr(
                    get_settings(), "speech_worker_url", "http://127.0.0.1:8095"
                )
                monkeypatch.setattr(
                    get_settings(), "speech_worker_token", "isolated-speech-test-key"
                )
                live = RemoteSpeech()
                assert live.health()["asr"] and live.health()["tts"]
                model = OllamaProvider(
                    Settings(
                        ollama_base_url="http://127.0.0.1:11434",
                        ollama_model="llama3.2:3b",
                    )
                )
                app.dependency_overrides[get_speech_provider] = lambda: live
                app.dependency_overrides[provider_dependency] = lambda: model
                french = "Bonjour, je voudrais une baguette, s’il vous plaît."
                real_wav = live.synthesize(french)
                new_sid = start(client)
                response = upload(client, new_sid, data=real_wav, retain=True)
                assert response.status_code == 200, response.text
                result = response.json()
                assert result["transcription_status"] == "transcribed", result
                assert (
                    result["tutor"] and result["tutor_audio"]["status"] == "ready"
                ), result
                print("LIVE voice transcript:", result["transcript"])
                print("LIVE tutor:", result["tutor"]["answer"])
                print(
                    "LIVE playable bytes:",
                    len(
                        client.get(
                            "/api/v1/speech/audio/" + result["tutor_audio"]["asset_id"]
                        ).content
                    ),
                )
                human = live.transcribe(
                    (
                        Path(__file__).parent / "fixtures/speech/fr-bonjour.ogg"
                    ).read_bytes()
                )
                assert "bonjour" in human.text.casefold(), human
                print("LIVE human fixture:", human.status, human.text)
                intro = client.post(f"/api/v1/speech/sessions/{new_sid}/text",
                    json={"message": "Bonjour, je m'appelle Camille. J'habite à Paris.", "request_id": str(uuid4())},
                    headers=_csrf(client))
                assert intro.status_code == 200, intro.text
                intro_reply = intro.json()
                assert intro_reply["tutor_audio"]["status"] == "ready", intro_reply
                assert intro_reply["tutor"]["answer"].count("?") <= 1
                assert len(intro_reply["tutor"]["answer"].split("\nEnglish:")[0].split()) <= 35
                print("LIVE introduction response:", intro_reply["tutor"]["answer"])
                # Real decoding/ASR, Ollama and Piper; inject only the uncertain
                # classification so the explicit-review branch is deterministic.
                class ReviewSpeech(RemoteSpeech):
                    def transcribe(self, data):
                        actual = super().transcribe(data)
                        assert actual.text and actual.language == "fr", actual
                        print("LIVE review original ASR:", actual.status, actual.text)
                        return actual.model_copy(update={"status": "uncertain"})

                app.dependency_overrides[get_speech_provider] = lambda: ReviewSpeech()
                recorded_messages = []
                class ObservedTutor:
                    def generate(self, messages, **kwargs):
                        recorded_messages.extend(messages)
                        return model.generate(messages, **kwargs)

                app.dependency_overrides[provider_dependency] = lambda: ObservedTutor()
                uncertain = upload(client, new_sid, data=(Path(__file__).parent / "fixtures/speech/fr-bonjour.ogg").read_bytes()).json()
                assert uncertain["transcription_status"] == "uncertain" and uncertain["tutor"] is None
                correction = "Bonjour, je m'appelle Camille. J'habite à Paris."
                reviewed = client.post(f"/api/v1/speech/sessions/{new_sid}/text", json={
                    "message": correction, "reviewed_turn_id": uncertain["id"], "request_id": str(uuid4())
                }, headers=_csrf(client))
                assert reviewed.status_code == 200, reviewed.text
                checked = reviewed.json()
                assert checked["review"]["confirmed_text"] == correction
                assert checked["review"]["original_text"] == uncertain["transcript"]
                assert checked["tutor_audio"]["status"] == "ready", checked
                assert any(correction in m["content"] for m in recorded_messages)
                audio = client.get("/api/v1/speech/audio/" + checked["tutor_audio"]["asset_id"])
                assert audio.status_code == 200 and audio.content.startswith(b"RIFF")
                print("LIVE corrected review:", checked["review"], "TTS bytes:", len(audio.content))
                assert (
                    client.post(
                        "/api/v1/auth/logout", headers=_csrf(client)
                    ).status_code
                    == 200
                )
                assert (
                    client.post(
                        "/api/v1/auth/login",
                        json={"email": account, "password": "StrongLearningPass2026"},
                    ).status_code
                    == 200
                )
                history = client.get("/api/v1/speech/sessions/" + new_sid).json()["turns"]
                assert any(t.get("review", {}).get("confirmed_text") == correction for t in history if t.get("review"))
                deletion_url = "/api/v1/speech/audio/" + result["input_audio_id"]
                deletion = client.delete(deletion_url, headers=_csrf(client))
                if deletion.status_code == 429:
                    # This long integration sequence legitimately reaches the
                    # unchanged per-user quota. Wait for its real window.
                    delay = int(deletion.headers["Retry-After"])
                    assert 0 <= delay <= 60
                    time.sleep(delay + 1)
                    deletion = client.delete(deletion_url, headers=_csrf(client))
                assert deletion.status_code == 200, deletion.text
                assert (
                    client.get(
                        "/api/v1/speech/audio/" + result["input_audio_id"]
                    ).status_code
                    == 404
                )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
