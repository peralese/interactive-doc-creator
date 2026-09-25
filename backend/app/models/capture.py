"""Capture ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDString


class Capture(Base):
    __tablename__ = "captures"

    id: Mapped[str] = mapped_column(
        UUIDString, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_transcription: Mapped[str] = mapped_column(String, nullable=False)
    clean_prose: Mapped[str | None] = mapped_column(String, nullable=True)
    structured_breakdown: Mapped[str | None] = mapped_column(String, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    progress_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    published_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
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

# Made with Bob
