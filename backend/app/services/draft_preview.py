from __future__ import annotations

from app.config import get_settings
from app.models import User


def can_author_drafts(user: User) -> bool:
    """Keep the existing administrator authoring gate separate from learning."""
    return bool(user.role == "admin" and user.is_active and user.email_verified_at is not None
        and get_settings().draft_learning_preview_enabled)


def can_preview_drafts(user: User) -> bool:
    settings = get_settings()
    return bool(user.is_active and user.email_verified_at is not None and (
        can_author_drafts(user)
        or (settings.personal_learning_preview_enabled
            and user.role == "learner" and user.id in settings.personal_preview_user_ids)
    ))
