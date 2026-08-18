"""Captures API endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import get_db
from ..models.capture import Capture
from ..schemas.capture import (
    CaptureCreate,
    CaptureListResponse,
    CaptureResponse,
    PolishRequest,
    PolishResponse,
)
from ..services.capture_service import CaptureService
from ..services.llm_provider import LLMProviderError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CaptureResponse, status_code=status.HTTP_201_CREATED)
async def create_capture(
    capture_data: CaptureCreate,
    db: AsyncSession = Depends(get_db),
):
    """Save a new capture."""
    capture = Capture(
        name=capture_data.name,
        raw_transcription=capture_data.raw_transcription,
        clean_prose=capture_data.clean_prose,
        structured_breakdown=capture_data.structured_breakdown,
        audio_path=capture_data.audio_path,
        llm_provider=capture_data.llm_provider,
    )
    db.add(capture)
    await db.commit()
    await db.refresh(capture)
    return capture


@router.get("/", response_model=CaptureListResponse)
async def list_captures(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all captures ordered by most recent first."""
    result = await db.execute(
        select(Capture).order_by(Capture.created_at.desc()).offset(skip).limit(limit)
    )
    captures = result.scalars().all()

    count_result = await db.execute(select(func.count(Capture.id)))
    total = count_result.scalar_one()

    return CaptureListResponse(captures=captures, total=total)


@router.get("/{capture_id}", response_model=CaptureResponse)
async def get_capture(
    capture_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single capture by ID."""
    capture = await db.get(Capture, str(capture_id))
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture {capture_id} not found",
        )
    return capture


@router.delete("/{capture_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_capture(
    capture_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a capture."""
    capture = await db.get(Capture, str(capture_id))
    if not capture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Capture {capture_id} not found",
        )
    await db.delete(capture)
    await db.commit()


@router.post("/polish", response_model=PolishResponse)
async def polish_capture(
    request: PolishRequest,
):
    """Polish raw transcription text using the chosen LLM provider.

    provider='ollama' keeps all data local on the machine.
    provider='openai' sends data to OpenAI's cloud API.
    """
    try:
        result = await CaptureService().polish(request.raw_text, request.provider)
        return PolishResponse(**result)
    except LLMProviderError as exc:
        logger.error("Capture polish failed (provider=%s): %s", request.provider, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The polishing service is currently unavailable. Your transcription has been preserved.",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error during capture polish: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="An unexpected error occurred. Your transcription has been preserved.",
        ) from exc

# Made with Bob
