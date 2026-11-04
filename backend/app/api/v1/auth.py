from __future__ import annotations

import secrets
import smtplib
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.core.database import get_db
from app.dependencies import AuthContext, current_auth_context, current_user, require_csrf, require_request_origin, safe_user_payload
from app.models import EmailVerificationToken, PasswordResetToken, User, UserPreferences, UserProfile, UserSession
from app.schemas import EmailRequest, LoginRequest, RegisterRequest, ResetPasswordRequest, TokenRequest
from app.security import hash_password, hash_token, new_opaque_token, utcnow, verify_password
from app.services.email import EmailService, get_email_service
from app.services.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> dict:
    require_request_origin(request)
    settings = get_settings()
    enforce_rate_limit(request, "register", limit=settings.registration_rate_limit, window_seconds=3600)
    if db.query(User.id).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to register with this email address.")

    user = User(email=payload.email, password_hash=hash_password(payload.password), role="learner")
    db.add(user)
    db.flush()
    age_band = None if payload.age is None else "under_18" if payload.age < 18 else "18_or_over"
    db.add(UserProfile(user_id=user.id, display_name=payload.display_name, registration_age_band=age_band))
    db.add(UserPreferences(user_id=user.id))
    token = _new_verification_token(db, user.id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to register with this email address.") from exc

    verification_link = f"{settings.frontend_origin}/verify-email#token={token}"
    _send_email(
        email_service,
        user.email,
        "Verify your FluentLoop AI email",
        f"Confirm your email using this link: {verification_link}\nThis link expires in 24 hours.",
    )
    return {"message": "Registration successful. Check your email to verify your account."}


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> dict:
    require_request_origin(request)
    enforce_rate_limit(request, "login", limit=10, window_seconds=900)
    user = (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.preferences))
        .filter(User.email == payload.email)
        .first()
    )
    if user is None:
        hash_password(payload.password)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not verify_password(user.password_hash, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if user.email_verified_at is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify your email before signing in.")

    settings = get_settings()
    raw_token = new_opaque_token()
    now = utcnow()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(seconds=settings.session_ttl_seconds),
        user_agent=request.headers.get("user-agent", "")[:256] or None,
    )
    user.last_login_at = now
    db.add(session)
    db.commit()
    csrf_token = secrets.token_urlsafe(32)
    _set_session_cookies(response, raw_token, csrf_token)
    return {"user": safe_user_payload(user)}


@router.get("/me")
def get_me(context: AuthContext = Depends(current_auth_context)) -> dict:
    return {"user": safe_user_payload(context.user)}


@router.post("/logout")
def logout(response: Response, context: AuthContext = Depends(require_csrf), db: Session = Depends(get_db)) -> dict:
    context.session.revoked_at = utcnow()
    db.commit()
    _clear_session_cookies(response)
    return {"message": "Signed out."}


@router.post("/logout-all")
def logout_all(
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    now = utcnow()
    db.query(UserSession).filter(
        UserSession.user_id == context.user.id,
        UserSession.revoked_at.is_(None),
    ).update({UserSession.revoked_at: now}, synchronize_session=False)
    db.commit()
    _clear_session_cookies(response)
    return {"message": "All sessions have been signed out."}


@router.post("/deactivate")
def deactivate_account(
    response: Response,
    context: AuthContext = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    now = utcnow()
    context.user.is_active = False
    db.query(UserSession).filter(
        UserSession.user_id == context.user.id,
        UserSession.revoked_at.is_(None),
    ).update({UserSession.revoked_at: now}, synchronize_session=False)
    db.commit()
    _clear_session_cookies(response)
    return {"message": "Account deactivated and sessions revoked."}


@router.get("/sessions")
def list_sessions(
    context: AuthContext = Depends(current_auth_context),
    db: Session = Depends(get_db),
) -> dict:
    sessions = db.query(UserSession).filter(
        UserSession.user_id == context.user.id,
        UserSession.revoked_at.is_(None),
        UserSession.expires_at > utcnow(),
    ).order_by(UserSession.created_at.desc()).all()
    return {
        "sessions": [
            {
                "id": str(session.id),
                "created_at": session.created_at.isoformat(),
                "last_used_at": session.last_used_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "user_agent": session.user_agent,
                "current": session.id == context.session.id,
            }
            for session in sessions
        ]
    }


@router.post("/verify-email")
def verify_email(
    payload: TokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_request_origin(request)
    token_record = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token_hash == hash_token(payload.token)
    ).first()
    now = utcnow()
    if token_record is None or token_record.consumed_at is not None or _expired(token_record.expires_at, now):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link is invalid or expired.")

    user = db.query(User).filter(User.id == token_record.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link is invalid or expired.")
    token_record.consumed_at = now
    user.email_verified_at = now
    db.commit()
    return {"message": "Email verified. You can now sign in."}


@router.post("/resend-verification")
def resend_verification(
    payload: EmailRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> dict:
    require_request_origin(request)
    enforce_rate_limit(request, "resend-verification", limit=3, window_seconds=3600)
    user = db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).first()
    if user is not None and user.email_verified_at is None:
        token = _new_verification_token(db, user.id)
        db.commit()
        settings = get_settings()
        link = f"{settings.frontend_origin}/verify-email#token={token}"
        _send_email(
            email_service,
            user.email,
            "Verify your FluentLoop AI email",
            f"Confirm your email: {link}",
            conceal_delivery_failure=True,
        )
    return {"message": "If the account needs verification, an email will be sent."}


@router.post("/forgot-password")
def forgot_password(
    payload: EmailRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> dict:
    require_request_origin(request)
    enforce_rate_limit(request, "forgot-password", limit=3, window_seconds=3600)
    user = db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).first()
    if user is not None:
        token = _new_password_reset_token(db, user.id)
        db.commit()
        settings = get_settings()
        link = f"{settings.frontend_origin}/reset-password#token={token}"
        _send_email(
            email_service,
            user.email,
            "Reset your FluentLoop AI password",
            f"Reset your password: {link}",
            conceal_delivery_failure=True,
        )
    return {"message": "If an account exists for this email, password reset instructions will be sent."}


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    require_request_origin(request)
    record = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == hash_token(payload.token)).first()
    now = utcnow()
    if record is None or record.consumed_at is not None or _expired(record.expires_at, now):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset link is invalid or expired.")

    user = db.query(User).filter(User.id == record.user_id, User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset link is invalid or expired.")

    record.consumed_at = now
    user.password_hash = hash_password(payload.password)
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None),
    ).update({UserSession.revoked_at: now}, synchronize_session=False)
    db.commit()
    return {"message": "Password reset successful. Please sign in with your new password."}


def _new_verification_token(db: Session, user_id) -> str:
    settings = get_settings()
    token = new_opaque_token()
    now = utcnow()
    db.add(EmailVerificationToken(
        user_id=user_id,
        token_hash=hash_token(token),
        created_at=now,
        expires_at=now + timedelta(seconds=settings.email_verification_ttl_seconds),
    ))
    return token


def _new_password_reset_token(db: Session, user_id) -> str:
    settings = get_settings()
    token = new_opaque_token()
    now = utcnow()
    db.add(PasswordResetToken(
        user_id=user_id,
        token_hash=hash_token(token),
        created_at=now,
        expires_at=now + timedelta(seconds=settings.password_reset_ttl_seconds),
    ))
    return token


def _send_email(
    email_service: EmailService,
    recipient: str,
    subject: str,
    body: str,
    conceal_delivery_failure: bool = False,
) -> None:
    try:
        email_service.send(recipient, subject, body)
    except (OSError, smtplib.SMTPException) as exc:
        if conceal_delivery_failure:
            logger.error("Authentication email delivery failed (%s).", type(exc).__name__)
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is temporarily unavailable. Please try again later.",
        ) from exc


def _set_session_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    settings = get_settings()
    common = {
        "max_age": settings.session_ttl_seconds,
        "secure": settings.cookie_secure,
        "httponly": True,
        "samesite": settings.cookie_samesite,
        "path": "/api/v1",
    }
    response.set_cookie(settings.session_cookie_name, session_token, **common)
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=settings.session_ttl_seconds,
        secure=settings.cookie_secure,
        httponly=False,
        samesite=settings.cookie_samesite,
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            name,
            path="/" if name == settings.csrf_cookie_name else "/api/v1",
            secure=settings.cookie_secure,
            httponly=name == settings.session_cookie_name,
            samesite=settings.cookie_samesite,
        )


def _expired(expires_at, now) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=now.tzinfo)
    return expires_at <= now
