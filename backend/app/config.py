import json
from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ReviewCategory = Literal["linguistic_accuracy", "phonetics", "pedagogy", "answer_keys", "licensing"]


class ReviewGrant(BaseModel):
    categories: set[ReviewCategory] = Field(min_length=1)
    qualification: Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=1000)]


class Settings(BaseSettings):
    app_name: str = "FluentLoop AI"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="APP_ENV")
    enable_draft_learning_preview: bool = Field(
        default=False, alias="ENABLE_DRAFT_LEARNING_PREVIEW"
    )
    development_register_limit: int = Field(default=30, alias="DEV_REGISTER_LIMIT")
    curriculum_reviewer_grants: dict[UUID, ReviewGrant] = Field(
        default_factory=dict, alias="CURRICULUM_REVIEWER_GRANTS"
    )
    api_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg://db:5432/fluentloop",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    session_cookie_name: str = Field(default="fluentloop_session", alias="SESSION_COOKIE_NAME")
    session_ttl_seconds: int = Field(default=60 * 60 * 24 * 14, alias="SESSION_TTL")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", alias="COOKIE_SAMESITE")
    csrf_cookie_name: str = Field(default="fluentloop_csrf", alias="CSRF_COOKIE_NAME")
    frontend_origin: str = Field(default="http://localhost:3000", alias="FRONTEND_ORIGIN")
    smtp_host: str = Field(default="mailpit", alias="SMTP_HOST")
    smtp_port: int = Field(default=1025, alias="SMTP_PORT")
    smtp_starttls: bool = Field(default=False, alias="SMTP_STARTTLS")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    email_from: str = Field(default="FluentLoop AI <no-reply@fluentloop.local>", alias="EMAIL_FROM")
    email_verification_ttl_seconds: int = Field(default=60 * 60 * 24, alias="EMAIL_VERIFICATION_TTL")
    password_reset_ttl_seconds: int = Field(default=60 * 60, alias="PASSWORD_RESET_TTL")
    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        alias="CORS_ORIGINS",
    )
    log_level: str = "INFO"
    ai_provider: str = "ollama"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    ai_request_timeout_seconds: int = Field(default=60, ge=1, le=180)
    ai_max_output_tokens: int = Field(default=600, ge=32, le=2000)
    ai_max_input_characters: int = Field(default=4000, ge=100, le=4000)
    ai_max_concurrent_requests: int = Field(default=1, ge=1, le=4)
    speech_worker_url: str = "http://speech-worker:8090"
    speech_worker_token: str = ""
    speech_asr_provider: str = "faster_whisper"
    speech_asr_model: str = Field(default="tiny", pattern="^(tiny|base)$")
    speech_asr_device: str = "cpu"
    speech_asr_compute_type: str = "int8"
    speech_tts_provider: str = "piper"
    speech_tts_voice: str = "fr_FR-siwis-medium"
    speech_model_path: str = "/models"
    speech_storage_path: str = "/tmp/fluentloop-private-audio"
    speech_max_upload_bytes: int = Field(default=5_000_000, ge=10000, le=10_000_000)
    speech_max_duration_seconds: int = Field(default=30, ge=1, le=30)
    speech_processing_timeout_seconds: int = Field(default=60, ge=5, le=120)
    speech_audio_retention_hours: int = Field(default=24, ge=1, le=24)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if value is None:
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001",
            ]

        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                raise ValueError("CORS_ORIGINS must be a JSON array of allowed origins.")

            try:
                parsed = json.loads(raw_value)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "CORS_ORIGINS must be a valid JSON array such as [\"http://localhost:3000\"]"
                ) from exc

            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise ValueError("CORS_ORIGINS must be a JSON array of strings.")

            return parsed

        return value

    @model_validator(mode="after")
    def validate_cookie_policy(self) -> "Settings":
        self.cookie_samesite = self.cookie_samesite.lower()
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none.")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SAMESITE=none requires COOKIE_SECURE=true.")
        if self.environment.lower() in {"prod", "production"} and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production.")
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must contain explicit origins and cannot include '*'.")
        if self.frontend_origin not in self.cors_origins:
            raise ValueError("FRONTEND_ORIGIN must be included in CORS_ORIGINS.")
        if self.session_ttl_seconds <= 0 or self.email_verification_ttl_seconds <= 0 or self.password_reset_ttl_seconds <= 0:
            raise ValueError("Session and token expiration periods must be positive.")
        if self.development_register_limit <= 0:
            raise ValueError("DEV_REGISTER_LIMIT must be positive.")
        return self

    @property
    def registration_rate_limit(self) -> int:
        if self.environment.lower() == "development":
            return self.development_register_limit
        return 5

    @property
    def draft_learning_preview_enabled(self) -> bool:
        return (
            self.environment.lower() == "development"
            and self.enable_draft_learning_preview
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
