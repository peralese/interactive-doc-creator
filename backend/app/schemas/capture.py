"""Capture Pydantic schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CaptureCreate(BaseModel):
    """Schema for creating a new capture."""

    name: str = Field(..., min_length=1, max_length=200, description="Capture name")
    raw_transcription: str = Field(..., min_length=1, description="Raw transcribed text")
    clean_prose: str | None = Field(None, description="LLM-polished prose version")
    structured_breakdown: str | None = Field(None, description="LLM structured breakdown")
    audio_path: str | None = Field(None, description="Path to saved audio file")
    llm_provider: str | None = Field(None, description="Provider used for polishing")


class CaptureResponse(BaseModel):
    """Schema for a single capture response."""

    id: UUID
    name: str
    raw_transcription: str
    clean_prose: str | None
    structured_breakdown: str | None
    audio_path: str | None
    llm_provider: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CaptureListResponse(BaseModel):
    """Schema for listing captures."""

    captures: list[CaptureResponse]
    total: int


class PolishRequest(BaseModel):
    """Schema for the polish endpoint request."""

    raw_text: str = Field(..., min_length=1, description="Raw transcription text to polish")
    provider: Literal["ollama", "openai"] = Field(
        default="ollama",
        description="LLM provider to use — ollama keeps data local, openai sends to cloud",
    )


class PolishResponse(BaseModel):
    """Schema for the polish endpoint response."""

    clean_prose: str = Field(..., description="Cleaned, polished prose version")
    structured_breakdown: str = Field(..., description="Structured breakdown of the idea")

# Made with Bob
