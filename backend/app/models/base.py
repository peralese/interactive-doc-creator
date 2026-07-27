"""Async SQLAlchemy engine, session factory, and database helpers."""

from __future__ import annotations

import uuid as _uuid_module

from sqlalchemy import String
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import TypeDecorator

from ..config import settings


class UUIDString(TypeDecorator):
    """Store UUIDs as VARCHAR(36) strings; accept both UUID objects and strings."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        return value  # keep as string; callers treat IDs as str


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


# Module-level engine and session factory — initialised by init_db()
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def AsyncSessionLocal() -> AsyncSession:
    """Return a new AsyncSession from the current factory.

    Callable so that ``async with AsyncSessionLocal() as db:`` works the same
    way whether the factory has been set by init_db() or overridden in tests.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _session_factory()


async def init_db() -> None:
    """Create the async engine, session factory, and all tables."""
    global _engine, _session_factory

    _engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        future=True,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Import models so their tables are registered on Base.metadata
    from . import response, session, template  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine cleanly on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    _session_factory = None


async def get_db():
    """FastAPI dependency that yields a per-request AsyncSession."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
