"""Response API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.base import get_db
from ..models.response import Response
from ..schemas.response import (
    ResponseCreate,
    ResponseUpdate,
    ResponseResponse,
    ResponseListResponse,
)
from ..services.session_manager import SessionManager

router = APIRouter()


@router.post("/", response_model=ResponseResponse, status_code=status.HTTP_201_CREATED)
async def create_response(
    response_data: ResponseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new response."""
    manager = SessionManager(db)
    try:
        await manager.get(response_data.session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response = Response(**response_data.model_dump())
    db.add(response)
    await manager.record_progress(
        response_data.session_id, response_data.sequence_number
    )
    await db.commit()
    await db.refresh(response)
    return response


@router.get("/session/{session_id}", response_model=ResponseListResponse)
async def list_session_responses(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List all responses for a session."""
    result = await db.execute(
        select(Response)
        .where(Response.session_id == session_id)
        .order_by(Response.sequence_number)
    )
    responses = result.scalars().all()
    
    return ResponseListResponse(responses=responses, total=len(responses))


@router.get("/{response_id}", response_model=ResponseResponse)
async def get_response(
    response_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific response by ID."""
    result = await db.execute(
        select(Response).where(Response.id == response_id)
    )
    response = result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Response {response_id} not found"
        )
    
    return response


@router.patch("/{response_id}", response_model=ResponseResponse)
async def update_response(
    response_id: UUID,
    response_data: ResponseUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a response."""
    result = await db.execute(
        select(Response).where(Response.id == response_id)
    )
    response = result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Response {response_id} not found"
        )
    
    update_data = response_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(response, field, value)
    
    await db.commit()
    await db.refresh(response)
    return response


@router.delete("/{response_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_response(
    response_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a response."""
    result = await db.execute(
        select(Response).where(Response.id == response_id)
    )
    response = result.scalar_one_or_none()
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Response {response_id} not found"
        )
    
    await db.delete(response)
    await db.commit()

# Made with Bob
