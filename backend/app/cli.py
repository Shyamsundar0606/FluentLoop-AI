from __future__ import annotations

import getpass

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import User, UserPreferences, UserProfile
from app.schemas import EmailRequest, validate_password_strength
from app.security import hash_password, utcnow


def create_admin(email: str) -> None:
    normalized_email = EmailRequest(email=email).email
    password = getpass.getpass("Administrator password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    validate_password_strength(password)

    db: Session = SessionLocal()
    try:
        if db.query(User.id).filter(User.role == "admin").first():
            raise SystemExit("An administrator already exists.")
        if db.query(User.id).filter(User.email == normalized_email).first():
            raise SystemExit("An account already uses this email.")

        user = User(
            email=normalized_email,
            password_hash=hash_password(password),
            role="admin",
            email_verified_at=utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(UserProfile(user_id=user.id, display_name=normalized_email.split("@", 1)[0]))
        db.add(UserPreferences(user_id=user.id))
        db.commit()
        print("Administrator account created.")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FluentLoop AI administrative commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin_parser = subparsers.add_parser("create-admin", help="Create the first administrator account")
    admin_parser.add_argument("email")
    arguments = parser.parse_args()

    if arguments.command == "create-admin":
        create_admin(arguments.email)
