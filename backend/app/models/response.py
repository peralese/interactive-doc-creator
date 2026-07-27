"""Response ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDString

if TYPE_CHECKING:
    from .session import Session


class Response(Base):
    __tablename__ = "responses"

    id: Mapped[str] = mapped_column(
        UUIDString, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        UUIDString, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section_id: Mapped[str] = mapped_column(String(100), nullable=False)
    question: Mapped[str] = mapped_column(String, nullable=False)
    answer: Mapped[str] = mapped_column(String, nullable=False)
    transcription_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_followup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parent_response_id: Mapped[str | None] = mapped_column(
        UUIDString, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    session: Mapped["Session"] = relationship("Session", back_populates="responses")
