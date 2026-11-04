from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import AuthContext, current_auth_context, require_admin, require_csrf, safe_user_payload
from app.core.database import get_db
from app.models import UserPreferences
from app.schemas import OnboardingRequest, PreferencesPatch, ProfilePatch

router = APIRouter(prefix="/users/me", tags=["users"])


@router.get("/profile")
def get_profile(context: AuthContext = Depends(current_auth_context)) -> dict:
    return {
        "id": str(context.user.id),
        "email": context.user.email,
        "role": context.user.role,
        "email_verified": context.user.email_verified_at is not None,
        "display_name": context.user.profile.display_name,
        "preferred_name": context.user.profile.preferred_name,
        "native_language": context.user.profile.native_language,
        "country": context.user.profile.country,
        "timezone": context.user.profile.timezone,
        "learning_goal": context.user.profile.learning_goal,
        "onboarding_completed": context.user.profile.onboarding_completed_at is not None,
    }


@router.patch("/profile")
def patch_profile(
    payload: ProfilePatch,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    profile = context.user.profile
    changes = payload.model_dump(exclude_unset=True)
    for key in ("display_name", "native_language", "timezone"):
        if key in changes and changes[key] is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} cannot be null.")
    for key, value in changes.items():
        setattr(profile, key, value)
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(profile)
    return {
        "display_name": profile.display_name,
        "preferred_name": profile.preferred_name,
        "native_language": profile.native_language,
        "country": profile.country,
        "timezone": profile.timezone,
        "learning_goal": profile.learning_goal,
        "onboarding_completed": profile.onboarding_completed_at is not None,
    }


@router.get("/preferences")
def get_preferences(context: AuthContext = Depends(current_auth_context)) -> dict:
    return _preferences_payload(context.user.preferences)


@router.patch("/preferences")
def patch_preferences(
    payload: PreferencesPatch,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if value is None and key != "target_level":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{key} cannot be null.")
    preferences = context.user.preferences
    for key, value in changes.items():
        setattr(preferences, key, value)
    preferences.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preferences)
    return _preferences_payload(preferences)


@router.post("/onboarding")
def complete_onboarding(
    payload: OnboardingRequest,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    preferences = context.user.preferences
    preferences.current_level = payload.current_level
    preferences.explanation_language = payload.explanation_language
    preferences.daily_study_minutes = payload.daily_study_minutes
    preferences.learning_focus = payload.learning_focus
    preferences.target_language = "French"
    context.user.profile.learning_goal = payload.learning_goal
    if context.user.profile.onboarding_completed_at is None:
        context.user.profile.onboarding_completed_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Onboarding saved.", "user": safe_user_payload(context.user)}


@router.get("/dashboard")
def get_dashboard(context: AuthContext = Depends(current_auth_context)) -> dict:
    user = context.user
    return {
        "user": safe_user_payload(user),
        "learning_context": {
            "target_language": user.preferences.target_language,
            "difficulty_level": user.preferences.current_level,
        },
        "planned_sections": [
            {"id": "courses", "title": "French courses", "status": "available"},
            {"id": "ai_tutor", "title": "AI tutor", "status": "coming_in_future_milestones"},
            {"id": "pronunciation", "title": "Pronunciation practice", "status": "coming_in_future_milestones"},
        ],
    }


@router.get("/admin-check")
def admin_only_check(_admin=Depends(require_admin)) -> dict:
    return {"status": "authorized"}


def _preferences_payload(preferences: UserPreferences) -> dict:
    return {
        "explanation_language": preferences.explanation_language,
        "target_language": preferences.target_language,
        "current_level": preferences.current_level,
        "target_level": preferences.target_level,
        "daily_study_minutes": preferences.daily_study_minutes,
        "learning_focus": preferences.learning_focus,
        "theme": preferences.theme,
        "audio_playback_speed": preferences.audio_playback_speed,
    }
