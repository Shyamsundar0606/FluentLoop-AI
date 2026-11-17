"""Operator-side replay before a restored database is exposed to users.

Call with a separately verified restored-database Session and the restricted current
ledger references. This module deliberately has no public HTTP endpoint.
"""
from uuid import UUID
from sqlalchemy import select
from app.models import User
from app.services.account_privacy import erase


def replay(db, account_references):
    references = {UUID(str(value)) for value in account_references}
    if len(references) > 1000:
        raise ValueError("Replay at most 1000 references per operator batch.")
    removed = 0
    for reference in sorted(references):
        user = db.scalar(select(User).where(User.id == reference).with_for_update())
        if user is None:
            continue
        try:
            erase(db, user)
        except Exception:
            db.rollback()
            raise
        removed += 1
    return dict(references=len(references), removed=removed)
