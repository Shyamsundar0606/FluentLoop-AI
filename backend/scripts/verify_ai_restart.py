"""Read and continue an isolated browser conversation after restarting its API."""

import os
from uuid import uuid4
import httpx
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.config import get_settings
from app.core.database import SessionLocal
from app.models import User
from app.ai.models import Conversation

assert make_url(get_settings().database_url).database.startswith("fluentloop_m05_")
with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == "ai-browser@example.com"))
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.mode == "grammar")
        .order_by(Conversation.created_at.desc())
    )
    assert conversation
    conversation_id = str(conversation.id)
with httpx.Client(
    base_url="http://127.0.0.1:8015", headers={"Origin": "http://127.0.0.1:3015"}
) as client:
    assert (
        client.post(
            "/api/v1/auth/login",
            json={
                "email": "ai-browser@example.com",
                "password": "IsolatedBrowserTest2026!",
            },
        ).status_code
        == 200
    )
    old = client.get("/api/v1/ai/conversations/" + conversation_id)
    assert old.status_code == 200
    assert len(old.json()["messages"]) >= 2
    headers = {"X-CSRF-Token": client.cookies.get("fluentloop_csrf")}
    payload = {"message": "Continue after the API restart.", "request_id": str(uuid4())}
    response = client.post(
        "/api/v1/ai/conversations/" + conversation_id + "/messages",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200, response.text
    replay = client.post(
        "/api/v1/ai/conversations/" + conversation_id + "/messages",
        json=payload,
        headers=headers,
    )
    assert replay.json()["message_id"] == response.json()["message_id"]
print(
    "PASS: existing PostgreSQL conversation read and continued after actual API process restart; replay remained idempotent"
)
