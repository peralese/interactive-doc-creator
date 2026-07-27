"""Response Pydantic schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ResponseCreate(BaseModel):
    """Schema for creating a new response."""
    
    session_id: UUID = Field(..., description="Session identifier")
    section_id: str = Field(..., description="Section identifier from template")
    question: str = Field(..., description="Question asked")
    answer: str = Field(..., description="User's answer")
    transcription_confidence: float | None = Field(
        None,
        description="Transcription confidence score (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    audio_path: str | None = Field(None, description="Path to audio file")
    sequence_number: int = Field(default=0, description="Question sequence number", ge=0)
    is_followup: bool = Field(default=False, description="Is this a follow-up question?")
    parent_response_id: UUID | None = Field(
        None,
        description="Parent response ID if this is a follow-up"
    )


class ResponseUpdate(BaseModel):
    """Schema for updating a response."""
    
    answer: str | None = None
    transcription_confidence: float | None = Field(None, ge=0.0, le=1.0)
    audio_path: str | None = None


class ResponseResponse(BaseModel):
    """Schema for response response."""
    
    id: UUID
    session_id: UUID
    section_id: str
    question: str
    answer: str
    transcription_confidence: float | None
    audio_path: str | None
    sequence_number: int
    is_followup: bool
    parent_response_id: UUID | None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class ResponseListResponse(BaseModel):
    """Schema for listing responses."""
    
    responses: list[ResponseResponse]
    total: int

# Made with Bob
