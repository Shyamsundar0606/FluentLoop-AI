import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.config import Settings
from app.services import rate_limit


class FakeRedis:
    def __init__(self) -> None:
        self.counts = {}

    def eval(self, _script, _keys, key, _window):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    def ttl(self, _key):
        return 30


def test_rate_limit_rejects_requests_over_limit(monkeypatch) -> None:
    monkeypatch.setattr(rate_limit, "redis_client", FakeRedis())
    request = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
        "scheme": "http",
        "query_string": b"",
    })

    rate_limit.enforce_rate_limit(request, "test-login", limit=2, window_seconds=60)
    rate_limit.enforce_rate_limit(request, "test-login", limit=2, window_seconds=60)
    with pytest.raises(HTTPException) as error:
        rate_limit.enforce_rate_limit(request, "test-login", limit=2, window_seconds=60)
    assert error.value.status_code == 429
    assert error.value.headers["Retry-After"] == "30"


def test_registration_limit_uses_configured_development_limit() -> None:
    settings = Settings(_env_file=None, APP_ENV="development", DEV_REGISTER_LIMIT=30)

    assert settings.registration_rate_limit == 30


@pytest.mark.parametrize("environment", ["production", "test", "staging"])
def test_registration_limit_remains_five_outside_development(environment: str) -> None:
    settings = Settings(
        _env_file=None,
        APP_ENV=environment,
        DEV_REGISTER_LIMIT=30,
        COOKIE_SECURE=environment == "production",
    )

    assert settings.registration_rate_limit == 5


def test_development_registration_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="DEV_REGISTER_LIMIT must be positive"):
        Settings(_env_file=None, APP_ENV="development", DEV_REGISTER_LIMIT=0)
