"""Authenticated, reauthenticated self-service privacy controls."""
from typing import Literal
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies import AuthContext, current_auth_context, require_csrf
from app.services import account_privacy
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/users/me", tags=["account privacy"])


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(min_length=1, max_length=128)
    section: str = Field(max_length=40)
    offset: int = Field(default=0, ge=0, le=1_000_000)


class DeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(min_length=1, max_length=128)
    confirmation: Literal["DELETE MY ACCOUNT"]


@router.get("/data-export")
def export_sections(context: AuthContext = Depends(current_auth_context)):
    return dict(sections=list(account_privacy.EXPORTS), page_limit=100)


@router.post("/data-export")
def export_data(payload: ExportRequest, request: Request,
                context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db)):
    enforce_rate_limit(request, f"data-export:{context.user.id}", 20, 60)
    account_privacy.reauthenticate(context.user, payload.password.get_secret_value())
    return account_privacy.export_page(db, context.user, payload.section, payload.offset)


@router.post("/delete-account", status_code=202)
def delete_account(payload: DeleteRequest, request: Request, response: Response,
                   context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db)):
    enforce_rate_limit(request, f"account-erasure:{context.user.id}", 3, 900)
    account_privacy.reauthenticate(context.user, payload.password.get_secret_value())
    receipt = account_privacy.erase(db, context.user)
    from app.api.v1.auth import _clear_session_cookies
    _clear_session_cookies(response)
    try:
        account_privacy.cleanup_erasure_jobs(db)
    except Exception:
        db.rollback()
        import logging
        logging.getLogger(__name__).warning("account_audio_erasure_retry_pending")
    return dict(message="Account and relational learning data permanently deleted. Private audio erasure is queued for retry if needed.",
                receipt=str(receipt))
