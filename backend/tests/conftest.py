from __future__ import annotations

from collections.abc import Iterator
from time import monotonic

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.services.email import get_email_service


class CapturedEmailService:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send(self, recipient: str, subject: str, text_body: str) -> None:
        self.messages.append({"recipient": recipient, "subject": subject, "body": text_body})


class IsolatedRateLimitRedis:
    def __init__(self) -> None:
        self._values: dict[str, int] = {}
        self._expires_at: dict[str, float] = {}

    def eval(self, _script: str, _key_count: int, key: str, window_seconds: int) -> int:
        if self.ttl(key) == -2:
            self._values.pop(key, None)
            self._expires_at.pop(key, None)
        count = self._values.get(key, 0) + 1
        self._values[key] = count
        if count == 1:
            self._expires_at[key] = monotonic() + int(window_seconds)
        return count

    def ttl(self, key: str) -> int:
        expires_at = self._expires_at.get(key)
        if expires_at is None or expires_at <= monotonic():
            return -2
        return int(expires_at - monotonic())


@pytest.fixture
def api_client(monkeypatch) -> Iterator[tuple[TestClient, sessionmaker, CapturedEmailService]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db: Session = test_sessions()
        try:
            yield db
        finally:
            db.close()

    email_service = CapturedEmailService()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = lambda: email_service
    monkeypatch.setattr("app.services.rate_limit.redis_client", IsolatedRateLimitRedis())

    with TestClient(app, headers={"Origin": "http://localhost:3000"}) as client:
        yield client, test_sessions, email_service

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
