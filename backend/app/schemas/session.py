"""Session Pydantic schemas."""

from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Any
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session status enumeration."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class SessionCreate(BaseModel):
    """Schema for creating a new session."""
    
    template_id: str = Field(..., description="Template identifier")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional session metadata"
    )


class SessionUpdate(BaseModel):
    """Schema for updating a session."""
    
    status: SessionStatus | None = None
    metadata: dict[str, Any] | None = None
    current_question_index: int | None = Field(None, ge=0)
    generated_document: str | None = None


class SessionAutosave(BaseModel):
    """Small, idempotent progress payload used by interactive clients."""

    metadata: dict[str, Any] | None = None
    current_question_index: int | None = Field(None, ge=0)


class SessionResponse(BaseModel):
    """Schema for session response."""
    
    id: UUID
    template_id: str
    status: SessionStatus
    metadata: dict[str, Any] = Field(validation_alias="session_metadata")
    current_question_index: int
    generated_document: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class SessionWithResponses(SessionResponse):
    """Schema for session with responses included."""
    
    responses: list["ResponseResponse"] = Field(default_factory=list)


class SessionListResponse(BaseModel):
    """Schema for listing sessions."""
    
    sessions: list[SessionResponse]
    total: int


# Import here to avoid circular dependency
from .response import ResponseResponse
SessionWithResponses.model_rebuild()

# Made with Bob
