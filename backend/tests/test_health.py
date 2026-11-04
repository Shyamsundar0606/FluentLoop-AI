import json

import pytest
from fastapi.testclient import TestClient
from pydantic_settings.sources import SettingsError

from app.config import Settings
from app.main import app

client = TestClient(app)


def test_live_endpoint() -> None:
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "FluentLoop AI"


def test_system_info_endpoint() -> None:
    response = client.get("/api/v1/system/info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_name"] == "FluentLoop AI"
    assert payload["api_version"] == "v1"


def test_ready_endpoint_returns_response() -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "FluentLoop AI"
    assert payload["database"]["status"] in {"connected", "unavailable"}
    assert payload["redis"]["status"] in {"connected", "unavailable"}


def test_settings_parse_json_cors_array(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", json.dumps(["http://localhost:3000", "http://127.0.0.1:3000"]))
    settings = Settings()
    assert settings.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_settings_reject_invalid_cors_array(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    with pytest.raises(SettingsError):
        Settings()
