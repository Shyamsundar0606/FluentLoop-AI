from __future__ import annotations

from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Level = Literal["a1", "a2", "b1", "b2", "c1", "c2"]
Focus = Literal["speaking", "listening", "reading", "writing", "balanced"]
Theme = Literal["light", "dark", "system"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=1, max_length=80, validation_alias=AliasChoices("full_name", "display_name"))
    age: Optional[int] = Field(default=None, ge=0, le=120, strict=True, exclude=True)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Display name is required.")
        return normalized

    @model_validator(mode="before")
    @classmethod
    def consistent_name(cls, value):
        if isinstance(value, dict) and "full_name" in value and "display_name" in value:
            if value["full_name"] != value["display_name"]:
                raise ValueError("Provide one consistent full name.")
        return value

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        validate_password_strength(self.password)
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class EmailRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().casefold()


class TokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class ResetPasswordRequest(TokenRequest):
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "ResetPasswordRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        validate_password_strength(self.password)
        return self


class ProfilePatch(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    preferred_name: Optional[str] = Field(default=None, max_length=80)
    native_language: Optional[str] = Field(default=None, min_length=2, max_length=32)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    learning_goal: Optional[str] = Field(default=None, max_length=80)

    @field_validator("display_name", "preferred_name", "native_language", "timezone", "learning_goal")
    @classmethod
    def strip_optional_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank.")
        return value

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Choose a valid IANA timezone.") from exc
        return value


class PreferencesPatch(BaseModel):
    explanation_language: Optional[Literal["English"]] = None
    target_language: Optional[Literal["French"]] = None
    current_level: Optional[Level] = None
    target_level: Optional[Level] = None
    daily_study_minutes: Optional[Literal[5, 10, 15, 20, 30]] = None
    learning_focus: Optional[Focus] = None
    theme: Optional[Theme] = None
    audio_playback_speed: Optional[float] = Field(default=None, ge=0.5, le=2.0)


class OnboardingRequest(BaseModel):
    current_level: Level = "a1"
    explanation_language: Literal["English"] = "English"
    learning_goal: Literal[
        "Daily conversations",
        "Living in France",
        "French for work",
        "French for university",
        "French examinations",
        "General fluency",
    ]
    daily_study_minutes: Literal[5, 10, 15, 20, 30] = 15
    learning_focus: Focus = "balanced"


def validate_password_strength(password: str) -> None:
    if not any(char.islower() for char in password) or not any(char.isupper() for char in password):
        raise ValueError("Password must include uppercase and lowercase letters.")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must include at least one number.")
    if password.isspace() or len(password.strip()) < 12:
        raise ValueError("Password must contain at least 12 non-whitespace characters.")


class SafeUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role: Literal["learner", "admin"]
    email_verified: bool
    display_name: str
    preferred_name: Optional[str] = None
    native_language: str
    country: Optional[str] = None
    timezone: str
    learning_goal: Optional[str] = None
    onboarding_completed: bool
    preferences: dict
