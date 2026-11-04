"""Opt-in real PostgreSQL + optional genuine Ollama checks. Never use app databases."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import get_db
from app.services.email import get_email_service
from app.api.v1.ai import provider_dependency
from app.ai.models import Message, Conversation
from app.ai.providers.ollama_provider import OllamaProvider
from app.config import Settings
from app.models import User
from conftest import CapturedEmailService, IsolatedRateLimitRedis
from test_ai import FakeProvider, create, send
from test_learning import (
    _register_and_login,
    _csrf,
    _import_content,
    _set_role,
    _draft_lesson_id,
)

URL = os.getenv("AI_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not URL, reason="Set AI_TEST_DATABASE_URL to a dedicated fluentloop_m05_* database"
)


def test_real_postgres_persistence_concurrency_and_optional_live_model(monkeypatch):
    from sqlalchemy.engine import make_url

    assert make_url(URL).database.startswith(
        "fluentloop_m05_"
    ), "Refusing non-isolated database"
    engine = create_engine(URL, pool_pre_ping=True)
    sessions = sessionmaker(bind=engine, autoflush=False)

    def db_dependency():
        with sessions() as db:
            yield db

    email = CapturedEmailService()
    fake = FakeProvider()
    app.dependency_overrides[get_db] = db_dependency
    app.dependency_overrides[get_email_service] = lambda: email
    app.dependency_overrides[provider_dependency] = lambda: fake
    monkeypatch.setattr(
        "app.services.rate_limit.redis_client", IsolatedRateLimitRedis()
    )
    account = f"pg-{uuid4().hex[:12]}@example.com"
    try:
        with TestClient(app, headers={"Origin": "http://localhost:3000"}) as client:
            _register_and_login(client, email, account)
            _import_content(sessions)
            c = create(client)
            rid = str(uuid4())
            ready = threading.Event()
            release = threading.Event()

            def wait():
                ready.set()
                assert release.wait(20)

            fake.callback = wait
            with ThreadPoolExecutor(max_workers=1) as pool:
                first = pool.submit(
                    send, client, c["id"], "Explain être and avoir", rid
                )
                assert ready.wait(10)
                try:
                    assert (
                        send(client, c["id"], "Second concurrent message").status_code
                        == 409
                    )
                finally:
                    release.set()
                response = first.result(20)
                assert response.status_code == 200, response.text
            fake.callback = None
            assert (
                send(client, c["id"], request_id=rid).json()["message_id"]
                == response.json()["message_id"]
            )
            with sessions() as db:
                assert (
                    db.scalar(
                        select(func.count(Message.id)).where(
                            Message.conversation_id == UUID(c["id"])
                        )
                    )
                    == 2
                )
                # No open transaction is held across inference (checked using a provider callback).
            with TestClient(
                app, headers={"Origin": "http://localhost:3000"}
            ) as reconnected:
                assert (
                    reconnected.post(
                        "/api/v1/auth/login",
                        json={"email": account, "password": "StrongLearningPass2026"},
                    ).status_code
                    == 200
                )
                assert (
                    len(
                        reconnected.get(f"/api/v1/ai/conversations/{c['id']}").json()[
                            "messages"
                        ]
                    )
                    == 2
                )
            for _ in range(2):
                failed = send(client, c["id"], "Follow-up")
                assert failed.status_code == 200
            # Import remains draft; preview role and environment are authorized only in this isolated DB.
            _set_role(sessions, account, "admin")
            preview = Settings(
                APP_ENV="development", ENABLE_DRAFT_LEARNING_PREVIEW=True
            )
            monkeypatch.setattr(
                "app.services.draft_preview.get_settings", lambda: preview
            )
            lesson_id = str(_draft_lesson_id(sessions))
            lesson = client.post(
                "/api/v1/learning/sessions",
                json={"lesson_id": lesson_id},
                headers=_csrf(client),
            )
            assert lesson.status_code in (200, 201), lesson.text
            lesson_session = lesson.json()
            for exercise in lesson_session["exercises"][:2]:
                from app.curriculum_models import ExerciseOption
                from app.learning_models import LearningSessionExercise

                with sessions() as db:
                    item = db.get(LearningSessionExercise, UUID(exercise["id"]))
                    wrong = db.scalar(
                        select(ExerciseOption.id)
                        .where(
                            ExerciseOption.exercise_id == item.source_exercise_id,
                            ExerciseOption.is_correct.is_(False),
                        )
                        .limit(1)
                    )
                    assert wrong
                # The real grading service creates evidence; no invented attempts.
                assert (
                    client.post(
                        f"/api/v1/learning/sessions/{lesson_session['id']}/answers",
                        json={
                            "session_exercise_id": exercise["id"],
                            "selected_option_id": str(wrong),
                            "idempotency_key": str(uuid4()),
                        },
                        headers=_csrf(client),
                    ).status_code
                    == 200
                )
            recommendations = client.post(
                "/api/v1/ai/recommendations/refresh", headers=_csrf(client)
            )
            assert recommendations.status_code == 200
            assert recommendations.json()[0]["recommendation_type"] == "lesson_review"
            assert (
                len(
                    recommendations.json()[0]["source_activity_reference"][
                        "exercise_attempt_ids"
                    ]
                )
                >= 2
            )
            if os.getenv("AI_LIVE_OLLAMA") == "1":
                live = OllamaProvider(
                    Settings(
                        ollama_base_url="http://127.0.0.1:11434",
                        ollama_model="llama3.2:3b",
                    )
                )
                assert live.health()
                app.dependency_overrides[provider_dependency] = lambda: live
                cases = [
                    (
                        "tutor",
                        "Explain être and avoir briefly with one French example.",
                    ),
                    ("grammar", "Explain bonjour and formal greetings."),
                    ("correction", "Je suis 24 ans."),
                ]
                for mode, question in cases:
                    conv = create(client, mode=mode)
                    result = send(client, conv["id"], question)
                    assert result.status_code == 200, result.text
                    data = result.json()
                    assert data["model"]["model_name"] == "llama3.2:3b"
                    assert data["answer"].strip()
                    if mode == "correction":
                        assert data["correction"]["has_errors"] is True
                        assert (
                            data["correction"]["corrected_text"].replace("’", "'")
                            == "J'ai 24 ans."
                        )
                    print(
                        f"LIVE {mode}: {data['grounding_status']}, sources={len(data['sources'])}, answer={data['answer'][:160]}"
                    )
                roleplay = client.post(
                    "/api/v1/ai/scenarios/a1-boulangerie/start", headers=_csrf(client)
                ).json()
                assert (
                    send(client, roleplay["id"], "Begin our practice.").status_code
                    == 200
                )
                # New application client/session resumes persisted messages.
                with TestClient(
                    app, headers={"Origin": "http://localhost:3000"}
                ) as resumed:
                    assert (
                        resumed.post(
                            "/api/v1/auth/login",
                            json={
                                "email": account,
                                "password": "StrongLearningPass2026",
                            },
                        ).status_code
                        == 200
                    )
                    assert resumed.get(
                        f"/api/v1/ai/conversations/{roleplay['id']}"
                    ).json()["messages"]
                    assert (
                        send(
                            resumed, roleplay["id"], "Une baguette, s’il vous plaît."
                        ).status_code
                        == 200
                    )
                live.client.close()
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
