from __future__ import annotations

import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import auth
from app.config import Settings
from app.main import app

from app.models import EmailVerificationToken, PasswordResetToken, User, UserSession
from app.security import hash_token, utcnow, verify_password

PASSWORD = "StrongPassphrase2026"


def register_user(client, emails, email="learner@example.com", display_name="French learner"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "display_name": display_name,
        },
    )
    match = re.search(r"/verify-email#token=([A-Za-z0-9_-]+)", emails.messages[-1]["body"]) if response.status_code == 201 else None
    return response, match.group(1) if match else None


def verify_user(client, token):
    return client.post("/api/v1/auth/verify-email", json={"token": token})


def login(client, email="learner@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("fluentloop_csrf")}


def test_registration_verification_login_and_safe_session(api_client):
    client, sessions, emails = api_client
    response, token = register_user(client, emails, email="Learner@Example.com")
    assert response.status_code == 201
    assert token
    assert "token" not in response.text.lower()

    with sessions() as db:
        user = db.query(User).filter(User.email == "learner@example.com").one()
        assert user.role == "learner"
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(user.password_hash, PASSWORD)
        assert user.profile.display_name == "French learner"
        assert user.preferences.current_level == "a1"
        assert db.query(EmailVerificationToken).one().token_hash == hash_token(token)

    assert verify_user(client, token).status_code == 200
    assert verify_user(client, token).status_code == 400
    failed_login = login(client, password="wrong-password")
    assert failed_login.status_code == 401
    assert failed_login.json()["detail"] == "Invalid email or password."

    response = login(client)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "password_hash" not in response.text
    assert "token_hash" not in response.text
    assert "httponly" in response.headers["set-cookie"].lower()
    session_token = client.cookies.get("fluentloop_session")
    with sessions() as db:
        record = db.query(UserSession).one()
        assert record.token_hash == hash_token(session_token)
        assert record.token_hash != session_token

    assert client.get("/api/v1/auth/me").status_code == 200


def test_registration_rejects_duplicate_and_never_grants_public_admin(api_client):
    client, sessions, emails = api_client
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": "ROLE@example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "display_name": "Learner",
            "role": "admin",
        },
    )
    assert response.status_code == 201
    duplicate = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": "role@example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "display_name": "Another",
        },
    )
    assert duplicate.status_code == 409
    weak = client.post(
        "/api/v1/auth/register",
        headers={"Origin": "http://localhost:3000"},
        json={
            "email": "weak@example.com",
            "password": "short",
            "confirm_password": "short",
            "display_name": "Weak password",
        },
    )
    assert weak.status_code == 422
    with sessions() as db:
        assert db.query(User).filter(User.email == "role@example.com").one().role == "learner"


def test_registration_rate_limit_returns_retry_after_without_creating_limited_user(api_client, monkeypatch):
    settings = Settings(_env_file=None, APP_ENV="test")
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    client, sessions, _emails = api_client
    for attempt in range(5):
        response, _token = register_user(client, _emails, email=f"limited-{attempt}@example.com")
        assert response.status_code == 201

    limited_email = "limited-5@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": limited_email,
            "password": PASSWORD,
            "confirm_password": PASSWORD,
            "display_name": "Rate limited learner",
        },
    )
    assert response.status_code == 429
    assert response.headers["retry-after"].isdigit()
    assert response.headers["access-control-expose-headers"] == "Retry-After"

    with sessions() as db:
        assert db.query(User).filter(User.email == limited_email).count() == 0


@pytest.mark.parametrize(
    ("environment", "expected_limit"),
    [("development", 30), ("production", 5)],
)
def test_registration_endpoint_uses_environment_specific_limit(
    api_client, monkeypatch, environment: str, expected_limit: int
) -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV=environment,
        DEV_REGISTER_LIMIT=30,
        COOKIE_SECURE=environment == "production",
    )
    observed_limits: list[tuple[int, int]] = []
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(
        auth,
        "enforce_rate_limit",
        lambda _request, _action, limit, window_seconds: observed_limits.append((limit, window_seconds)),
    )

    client, _sessions, emails = api_client
    response, _token = register_user(client, emails, email=f"{environment}@example.com")

    assert response.status_code == 201
    assert observed_limits == [(expected_limit, 3600)]


def test_protected_profile_csrf_and_cross_user_isolation(api_client):
    client_a, sessions, emails = api_client
    unauthenticated = client_a.get("/api/v1/users/me/profile")
    assert unauthenticated.status_code == 401

    response, token = register_user(client_a, emails)
    assert response.status_code == 201
    assert verify_user(client_a, token).status_code == 200
    assert login(client_a).status_code == 200

    csrf_rejected = client_a.patch(
        "/api/v1/users/me/profile",
        json={"display_name": "Changed"},
    )
    assert csrf_rejected.status_code == 403

    client_b = TestClient(app, headers={"Origin": "http://localhost:3000"})
    response, token_b = register_user(client_b, emails, "second@example.com", "Second learner")
    assert response.status_code == 201
    assert verify_user(client_b, token_b).status_code == 200
    assert login(client_b, "second@example.com").status_code == 200
    changed = client_b.patch(
        "/api/v1/users/me/profile",
        headers=csrf_headers(client_b),
        json={"display_name": "Second updated"},
    )
    assert changed.status_code == 200
    assert client_b.get("/api/v1/users/me/profile").json()["display_name"] == "Second updated"
    assert client_a.get("/api/v1/users/me/profile").json()["display_name"] == "French learner"
    changed_level = client_a.patch(
        "/api/v1/users/me/preferences",
        headers=csrf_headers(client_a),
        json={"current_level": "c1"},
    )
    assert changed_level.status_code == 200
    assert changed_level.json()["current_level"] == "c1"
    assert client_a.get("/api/v1/users/me/dashboard").json()["user"]["preferences"]["current_level"] == "c1"
    assert client_b.get("/api/v1/users/me/preferences").json()["current_level"] == "a1"
    assert client_a.get("/api/v1/users/me/admin-check").status_code == 403

    with sessions() as db:
        assert db.query(User).filter(User.role == "learner").count() == 2


def test_all_supported_levels_persist_and_are_exposed_as_learning_context(api_client):
    client, sessions, emails = api_client
    _, token = register_user(client, emails)
    assert verify_user(client, token).status_code == 200
    assert login(client).status_code == 200

    for level in ("a1", "a2", "b1", "b2", "c1", "c2"):
        response = client.patch(
            "/api/v1/users/me/preferences",
            headers=csrf_headers(client),
            json={"current_level": level, "target_level": level},
        )
        assert response.status_code == 200
        assert response.json()["current_level"] == level
        assert response.json()["target_level"] == level
        dashboard = client.get("/api/v1/users/me/dashboard").json()
        assert dashboard["user"]["preferences"]["current_level"] == level
        assert dashboard["learning_context"] == {
            "target_language": "French",
            "difficulty_level": level,
        }

    with sessions() as db:
        preferences = db.query(User).one().preferences
        assert preferences.current_level == "c2"
        assert preferences.target_level == "c2"


def test_preference_onboarding_update_and_session_logout(api_client):
    client, sessions, emails = api_client
    _, token = register_user(client, emails)
    assert verify_user(client, token).status_code == 200
    assert login(client).status_code == 200
    response = client.post(
        "/api/v1/users/me/onboarding",
        headers=csrf_headers(client),
        json={
            "current_level": "b2",
            "explanation_language": "English",
            "learning_goal": "Daily conversations",
            "daily_study_minutes": 10,
            "learning_focus": "balanced",
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["onboarding_completed"] is True
    assert response.json()["user"]["preferences"]["current_level"] == "b2"
    assert response.json()["user"]["preferences"]["daily_study_minutes"] == 10
    with sessions() as db:
        assert db.query(User).one().preferences.current_level == "b2"
    invalid_level = client.patch(
        "/api/v1/users/me/preferences",
        headers=csrf_headers(client),
        json={"current_level": "pre_a1"},
    )
    assert invalid_level.status_code == 422
    invalid_target = client.patch(
        "/api/v1/users/me/preferences",
        headers=csrf_headers(client),
        json={"target_level": "a0"},
    )
    assert invalid_target.status_code == 422
    bad_preferences = client.patch(
        "/api/v1/users/me/preferences",
        headers=csrf_headers(client),
        json={"explanation_language": "Tamil"},
    )
    assert bad_preferences.status_code == 422
    updated = client.patch(
        "/api/v1/users/me/preferences",
        headers=csrf_headers(client),
        json={"theme": "dark", "audio_playback_speed": 1.2},
    )
    assert updated.status_code == 200
    assert updated.json()["theme"] == "dark"

    assert client.post("/api/v1/auth/logout", headers=csrf_headers(client)).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    with sessions() as db:
        assert db.query(UserSession).one().revoked_at is not None


def test_password_reset_revokes_sessions_and_token_is_single_use(api_client):
    client, sessions, emails = api_client
    _, verify_token = register_user(client, emails)
    assert verify_user(client, verify_token).status_code == 200
    assert login(client).status_code == 200
    assert client.post("/api/v1/auth/forgot-password", json={"email": "learner@example.com"}).status_code == 200
    match = re.search(r"/reset-password#token=([A-Za-z0-9_-]+)", emails.messages[-1]["body"])
    assert match
    reset_token = match.group(1)

    updated_password = "EvenStrongerPassphrase2026"
    payload = {"token": reset_token, "password": updated_password, "confirm_password": updated_password}
    response = client.post("/api/v1/auth/reset-password", json=payload)
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/reset-password", json=payload).status_code == 400

    with sessions() as db:
        user = db.query(User).one()
        assert verify_password(user.password_hash, updated_password)
        assert db.query(PasswordResetToken).one().consumed_at is not None
        assert db.query(UserSession).one().revoked_at is not None

    assert login(client, password=updated_password).status_code == 200


def test_expired_session_is_rejected_and_logout_all_revokes_everywhere(api_client):
    client_a, sessions, emails = api_client
    _, verification = register_user(client_a, emails)
    assert verify_user(client_a, verification).status_code == 200
    assert login(client_a).status_code == 200
    client_b = TestClient(app, headers={"Origin": "http://localhost:3000"})
    assert login(client_b).status_code == 200

    with sessions() as db:
        session = db.query(UserSession).first()
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client_a.get("/api/v1/auth/me").status_code == 401

    # Restore a valid session to exercise all-device revocation.
    client_a.cookies.clear()
    assert login(client_a).status_code == 200
    response = client_a.post("/api/v1/auth/logout-all", headers=csrf_headers(client_a))
    assert response.status_code == 200
    assert client_a.get("/api/v1/auth/me").status_code == 401
    assert client_b.get("/api/v1/auth/me").status_code == 401


def test_verification_token_expiration_and_origin_validation(api_client):
    client, sessions, emails = api_client
    _, token = register_user(client, emails)
    with sessions() as db:
        verification = db.query(EmailVerificationToken).one()
        verification.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    expired = verify_user(client, token)
    assert expired.status_code == 400
    rejected_origin = client.post(
        "/api/v1/auth/forgot-password",
        headers={"Origin": "https://attacker.invalid"},
        json={"email": "learner@example.com"},
    )
    assert rejected_origin.status_code == 403
