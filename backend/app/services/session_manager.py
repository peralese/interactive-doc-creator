"""Session state, autosave, resume, and cleanup operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..models.session import Session, SessionStatus


class SessionManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, session_id: UUID, *, load_responses: bool = False) -> Session:
        stmt = select(Session).where(Session.id == session_id)
        if load_responses:
            stmt = stmt.options(selectinload(Session.responses))
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise LookupError(f"Session {session_id} not found")
        return session

    async def autosave(
        self,
        session_id: UUID,
        *,
        metadata: dict[str, Any] | None = None,
        current_question_index: int | None = None,
    ) -> Session:
        session = await self.get(session_id)
        if metadata is not None:
            session.session_metadata = metadata
        if current_question_index is not None:
            session.current_question_index = current_question_index
        await self.db.flush()
        return session

    async def record_progress(self, session_id: UUID, sequence_number: int) -> Session:
        session = await self.get(session_id)
        session.current_question_index = max(
            session.current_question_index, sequence_number + 1
        )
        await self.db.flush()
        return session

    async def resume(self, session_id: UUID) -> Session:
        """Return a session with eagerly loaded responses."""
        return await self.get(session_id, load_responses=True)

    async def cleanup_expired(self, *, include_active: bool = False) -> int:
        """Delete expired sessions when explicitly invoked by maintenance code."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings.session_timeout_minutes
        )
        statuses = [SessionStatus.ABANDONED]
        if include_active:
            statuses.append(SessionStatus.ACTIVE)
        result = await self.db.execute(
            delete(Session)
            .where(Session.status.in_(statuses), Session.updated_at < cutoff)
            .returning(Session.id)
        )
        return len(result.scalars().all())
