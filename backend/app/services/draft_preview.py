from __future__ import annotations

from app.config import get_settings
from app.models import User


def can_preview_drafts(user: User) -> bool:
    return bool(user.role == "admin" and user.is_active and user.email_verified_at is not None
        and get_settings().draft_learning_preview_enabled)
