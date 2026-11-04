"""Explicit local-only fake-provider API for browser integration tests.

Never imported by production startup. Requires a dedicated test database and flag.
"""

import os
import json
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.engine import make_url
from app.config import get_settings

settings = get_settings()
assert os.environ.get("AI_E2E_TEST_SERVER") == "1"
assert make_url(settings.database_url).database.startswith(("fluentloop_m05_", "fluentloop_m06_"))
assert settings.environment in {"test", "development"}

from app.main import app
from app.api.v1.ai import provider_dependency
from app.ai.providers.base import Generation
from app.core.database import SessionLocal
from app.models import User, UserProfile, UserPreferences, utcnow
from app.security import hash_password
from app.content_import import _import_data, load_content
from pathlib import Path


class BrowserProvider:
    def health(self):
        return True

    def generate(self, messages, *, structured=None):
        if structured:
            answer = json.dumps(
                dict(
                    original_text=messages[-1]["content"],
                    corrected_text="J'ai 24 ans.",
                    has_errors=True,
                    explanations=["Use avoir to express age."],
                    alternative_expressions=[],
                    level="A1",
                    model_notes="",
                )
            )
        else:
            answer = "Bonjour ! Être means to be; avoir means to have. Je suis ici. J’ai un livre."
        return Generation(answer, "deterministic-browser-test")


class TestRateRedis:
    def __init__(self):
        self.values = {}
        self.expiry = {}

    def eval(self, _script, _count, key, _window):
        from time import monotonic
        if monotonic()>=self.expiry.get(key,0):
            self.values[key]=0
            self.expiry[key]=monotonic()+int(_window)
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    def ttl(self, key):
        from time import monotonic
        return max(1,int(self.expiry.get(key,0)-monotonic()))


from app.services import rate_limit

rate_limit.redis_client = TestRateRedis()
app.dependency_overrides[provider_dependency] = lambda: BrowserProvider()

with SessionLocal.begin() as db:
    from app.curriculum_models import CefrLevel

    for rank, level in enumerate(("A1", "A2", "B1", "B2", "C1", "C2"), 1):
        if not db.scalar(select(CefrLevel).where(CefrLevel.code == level)):
            db.add(
                CefrLevel(code=level, display_name=level, description=level, rank=rank)
            )
    db.flush()
    _import_data(
        db, load_content(Path(__file__).resolve().parents[1] / "content/a1/course.json")
    )
    for email, role in [
        ("ai-browser@example.com", "admin"),
        ("ai-other@example.com", "learner"),
    ]:
        if not db.scalar(select(User).where(User.email == email)):
            user = User(
                email=email,
                password_hash=hash_password("IsolatedBrowserTest2026!"),
                role=role,
                email_verified_at=utcnow(),
            )
            db.add(user)
            db.flush()
            db.add(
                UserProfile(
                    user_id=user.id,
                    display_name="Browser test",
                    onboarding_completed_at=utcnow(),
                )
            )
            db.add(UserPreferences(user_id=user.id))
