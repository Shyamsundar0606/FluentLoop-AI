from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.database import get_db
from app.models import User, UserSession
from app.security import hash_token, utcnow


@dataclass
class AuthContext:
    user: User
    session: UserSession


def current_auth_context(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthContext:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    session = db.query(UserSession).filter(UserSession.token_hash == hash_token(token)).first()
    now = utcnow()
    if (
        session is None
        or session.revoked_at is not None
        or _as_utc(session.expires_at) <= now
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None or not user.is_active:
        if session.revoked_at is None:
            session.revoked_at = now
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    session.last_used_at = now
    db.commit()
    return AuthContext(user=user, session=session)


def current_user(context: AuthContext = Depends(current_auth_context)) -> User:
    return context.user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required.")
    return user


def require_request_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    settings = get_settings()
    if not origin or origin not in settings.cors_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request origin is not allowed.")


def require_csrf(request: Request, context: AuthContext = Depends(current_auth_context)) -> AuthContext:
    require_request_origin(request)
    settings = get_settings()
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get("x-csrf-token")
    if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed.")
    return context


def safe_user_payload(user: User) -> dict:
    profile = user.profile
    preferences = user.preferences
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "email_verified": user.email_verified_at is not None,
        "display_name": profile.display_name if profile else "",
        "preferred_name": profile.preferred_name if profile else None,
        "native_language": profile.native_language if profile else "English",
        "country": profile.country if profile else None,
        "timezone": profile.timezone if profile else "UTC",
        "learning_goal": profile.learning_goal if profile else None,
        "onboarding_completed": profile.onboarding_completed_at is not None if profile else False,
        "preferences": {
            "explanation_language": preferences.explanation_language,
            "target_language": preferences.target_language,
            "current_level": preferences.current_level,
            "target_level": preferences.target_level,
            "daily_study_minutes": preferences.daily_study_minutes,
            "learning_focus": preferences.learning_focus,
            "theme": preferences.theme,
            "audio_playback_speed": preferences.audio_playback_speed,
        } if preferences else {},
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
