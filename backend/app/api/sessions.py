"""Session API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ..models.base import get_db
from ..models.session import Session
from ..models.template import Template
from ..schemas.session import (
    SessionCreate,
    SessionAutosave,
    SessionUpdate,
    SessionResponse,
    SessionWithResponses,
    SessionListResponse,
)
from ..services.session_manager import SessionManager

router = APIRouter()


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new document session."""
    template = await db.get(Template, session_data.template_id)
    session = Session(
        template_id=session_data.template_id,
        name=session_data.name,
        output_type=session_data.output_type or (template.output_type if template else None) or "report",
        session_metadata=session_data.metadata
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/", response_model=SessionListResponse)
async def list_sessions(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List resumable sessions that contain at least one saved response."""
    has_responses = Session.responses.any()
    result = await db.execute(
        select(Session)
        .where(has_responses)
        .order_by(Session.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sessions = result.scalars().all()

    count_result = await db.execute(
        select(func.count(Session.id)).where(has_responses)
    )
    total = count_result.scalar_one()
    
    return SessionListResponse(sessions=sessions, total=total)


@router.get("/{session_id}", response_model=SessionWithResponses)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific session by ID."""
    result = await db.execute(
        select(Session).where(Session.id == session_id).options(selectinload(Session.responses))
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return session


@router.post("/{session_id}/autosave", response_model=SessionResponse)
async def autosave_session(
    session_id: UUID,
    session_data: SessionAutosave,
    db: AsyncSession = Depends(get_db),
):
    """Persist interview progress without completing the session."""
    try:
        session = await SessionManager(db).autosave(
            session_id,
            name=session_data.name,
            output_type=session_data.output_type,
            metadata=session_data.metadata,
            current_question_index=session_data.current_question_index,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/{session_id}/resume", response_model=SessionWithResponses)
async def resume_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Resume a session with its saved responses and progress."""
    try:
        return await SessionManager(db).resume(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID,
    session_data: SessionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    # Update fields
    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "metadata":
            field = "session_metadata"
        setattr(session, field, value)
    
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a session."""
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    await db.delete(session)
    await db.commit()

# Made with Bob
