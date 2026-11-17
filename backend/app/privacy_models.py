"""Restricted pseudonymous erasure receipts and durable private-file cleanup."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.curriculum_models import STRUCTURED_JSON
from app.models import utcnow


class AccountErasureJob(Base):
    __tablename__ = "account_erasure_jobs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    storage_keys: Mapped[list] = mapped_column(STRUCTURED_JSON, nullable=False)
    account_reference: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
