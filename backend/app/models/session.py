"""Session ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base, UUIDString

if TYPE_CHECKING:
    from .response import Response


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        UUIDString, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    template_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    output_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus), nullable=False, default=SessionStatus.ACTIVE
    )
    session_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    current_question_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    # Rough draft assembled from the answers without an LLM (a cache; always rebuildable).
    generated_document: Mapped[str | None] = mapped_column(String, nullable=True)
    # "Refine with AI" output, kept separately so it never replaces the rough draft.
    refined_document: Mapped[str | None] = mapped_column(String, nullable=True)
    # True once answers change after refining; the refined text is kept but out of date.
    refined_stale: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
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

    def invalidate_documents(self) -> None:
        """Call whenever answers change: drop the draft cache, flag the refined text."""
        self.generated_document = None
        if self.refined_document:
            self.refined_stale = True

    responses: Mapped[list["Response"]] = relationship(
        "Response", back_populates="session", cascade="all, delete-orphan"
    )
