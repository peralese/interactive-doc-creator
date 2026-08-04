"""Template Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TemplateSection(BaseModel):
    """Schema for a template section."""
    
    id: str = Field(..., description="Section identifier")
    title: str = Field(..., description="Section title")
    description: str = Field(..., description="Section description")
    required: bool = Field(default=True, description="Is this section required?")
    question_hints: list[str] = Field(
        default_factory=list,
        description="Hints for generating questions"
    )


class TemplateCreate(BaseModel):
    """Schema for creating a new template."""
    
    id: str = Field(..., description="Template identifier", min_length=1, max_length=100)
    name: str = Field(..., description="Template name", min_length=1, max_length=200)
    description: str | None = Field(None, description="Template description")
    version: str = Field(default="1.0", description="Template version")
    content: dict[str, Any] = Field(..., description="Template content structure")
    category: str | None = Field(None, description="Template category")
    output_type: str | None = Field(None, description="Default output type")
    estimated_duration: int | None = Field(
        None,
        description="Estimated duration in minutes",
        ge=1
    )
    difficulty: str | None = Field(
        None,
        description="Difficulty level (beginner, intermediate, advanced)"
    )
    is_active: bool = Field(default=True, description="Is template active?")


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""
    
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    version: str | None = None
    content: dict[str, Any] | None = None
    category: str | None = None
    output_type: str | None = None
    estimated_duration: int | None = Field(None, ge=1)
    difficulty: str | None = None
    is_active: bool | None = None


class TemplateResponse(BaseModel):
    """Schema for template response."""
    
    id: str
    name: str
    description: str | None
    version: str
    content: dict[str, Any]
    category: str | None
    output_type: str | None
    estimated_duration: int | None
    difficulty: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    """Schema for listing templates."""
    
    templates: list[TemplateResponse]
    total: int


class TemplateIngestionResponse(BaseModel):
    """Unpublished template draft created from requirement text."""

    template: TemplateCreate
    analysis_mode: str
    warnings: list[str] = Field(default_factory=list)

# Made with Bob
