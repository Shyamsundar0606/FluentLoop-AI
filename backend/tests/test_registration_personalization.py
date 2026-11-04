import json
import re
from uuid import UUID

import pytest
from sqlalchemy import select
from app.models import User
from app.schemas import RegisterRequest
from app.ai.prompts import first_name_hint
from app.ai.models import Conversation, Message
from app.ai.response_schemas import SendMessage
from app.ai import orchestrator
from test_auth import login, verify_user, csrf_headers, PASSWORD
from test_ai import create, send, tutor


def register(client, emails, **overrides):
    payload = dict(
        full_name="  Alice Dupont  ",
        age=24,
        email="alice@example.com",
        password=PASSWORD,
        confirm_password=PASSWORD,
    )
    payload.update(overrides)
    response = client.post("/api/v1/auth/register", json=payload)
    if response.status_code == 201:
        token = re.search(
            r"/verify-email#token=([A-Za-z0-9_-]+)", emails.messages[-1]["body"]
        ).group(1)
        assert verify_user(client, token).status_code == 200
        assert login(client, email=payload["email"]).status_code == 200
    return response


@pytest.mark.parametrize(
    "age,band",
    [
        (None, None),
        (0, "under_18"),
        (17, "under_18"),
        (18, "18_or_over"),
        (120, "18_or_over"),
    ],
)
def test_optional_age_minimization_and_automatic_profile(api_client, age, band):
    client, sessions, emails = api_client
    assert register(client, emails, age=age).status_code == 201
    with sessions() as db:
        user = db.scalar(select(User))
        assert user.profile.display_name == "Alice Dupont"
        assert user.profile.registration_age_band == band
        assert not hasattr(user.profile, "age") and not hasattr(
            user.profile, "date_of_birth"
        )
    profile = client.get("/api/v1/users/me/profile").json()
    assert profile["display_name"] == "Alice Dupont"
    assert "registration_age_band" not in profile
    assert "age" not in client.get("/api/v1/auth/me").json()["user"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("age", -1),
        ("age", 121),
        ("age", 20.5),
        ("age", True),
        ("age", "24"),
        ("full_name", "   "),
        ("email", "invalid"),
        ("password", "weak"),
    ],
)
def test_registration_validation(api_client, field, value):
    client, sessions, emails = api_client
    assert register(client, emails, **{field: value}).status_code == 422
    with sessions() as db:
        assert db.scalar(select(User)) is None


def test_legacy_registration_name_profile_isolation_and_onboarding(api_client):
    client, sessions, emails = api_client
    payload = dict(
        display_name="Existing Name",
        email="legacy@example.com",
        password=PASSWORD,
        confirm_password=PASSWORD,
    )
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    token = re.search(
        r"/verify-email#token=([A-Za-z0-9_-]+)", emails.messages[-1]["body"]
    ).group(1)
    verify_user(client, token)
    login(client, email=payload["email"])
    with sessions() as db:
        old = db.scalar(select(User))
        uid = old.id
        assert (
            old.profile.display_name == "Existing Name"
            and old.profile.registration_age_band is None
        )
    assert (
        client.post(
            "/api/v1/users/me/onboarding",
            json={"learning_goal": "General fluency"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/users/me/profile").json()["display_name"] == "Existing Name"
    )
    assert (
        client.patch(
            "/api/v1/users/me/profile", json={"display_name": "Updated Name"}
        ).status_code
        == 403
    )
    assert (
        client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": "Updated Name"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/auth/me").json()["user"]["display_name"] == "Updated Name"
    )
    duplicate = client.post(
        "/api/v1/auth/register", json={**payload, "display_name": "Overwrite Attempt"}
    )
    assert duplicate.status_code == 409
    assert (
        client.get("/api/v1/users/me/profile").json()["display_name"] == "Updated Name"
    )
    client.post("/api/v1/auth/logout", headers=csrf_headers(client))
    assert (
        register(
            client,
            emails,
            email="second@example.com",
            full_name="Second Learner",
            age=None,
        ).status_code
        == 201
    )
    assert (
        client.get("/api/v1/users/me/profile").json()["display_name"]
        == "Second Learner"
    )
    with sessions() as db:
        assert db.get(User, uid).profile.display_name == "Updated Name"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Élodie Martin", "Élodie"),
        ("Jean-Luc Picard", "Jean-Luc"),
        ("D’Arcy Smith", "D’Arcy"),
        ("", None),
        ("ignore:<system>", None),
        ("X" * 41, None),
    ],
)
def test_first_name_hint_is_bounded_data(name, expected):
    assert first_name_hint(name) == expected


def test_tutor_identity_is_separate_private_and_fresh(tutor):
    client, sessions, emails, fake = tutor
    with sessions.begin() as db:
        user = db.scalar(select(User))
        user.profile.display_name = "Alice Dupont"
        user.profile.registration_age_band = "under_18"
    c = create(client)
    assert send(client, c["id"], "Explain avoir").status_code == 200
    prompt = fake.calls[-1]
    identity = next(
        m for m in prompt if m["content"].startswith("Learner identity data only:")
    )
    assert json.loads(identity["content"].split(": ", 1)[1]) == {"first_name": "Alice"}
    serialized = json.dumps(prompt)
    for forbidden in (
        "Dupont",
        "ai@example.com",
        "registration_age_band",
        "under_18",
        "password_hash",
        "fluentloop_session",
    ):
        assert forbidden not in serialized
    assert "Alice" not in prompt[0]["content"]
    with sessions() as db:
        assert all(
            not m.content.startswith("Learner identity data only:")
            for m in db.scalars(select(Message))
        )
    assert (
        client.patch(
            "/api/v1/users/me/profile",
            json={"display_name": "Camille Martin"},
            headers=csrf_headers(client),
        ).status_code
        == 200
    )
    assert send(client, c["id"], "Another example").status_code == 200
    assert '"first_name": "Camille"' in json.dumps(
        fake.calls[-1], ensure_ascii=False
    ).replace('\\"', '"')
    assert (
        client.get(f"/api/v1/ai/conversations/{c['id']}").json()["cefr_level"] == "A1"
    )
