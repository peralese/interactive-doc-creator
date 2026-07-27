"""Template API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import get_db
from ..models.template import Template
from ..schemas.template import (
    TemplateCreate,
    TemplateIngestionResponse,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdate,
)
from ..services.llm_provider import LLMProviderError, create_llm_provider
from ..services.requirements_ingestion import (
    RequirementsIngestionError,
    RequirementsIngestionService,
)

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    db: DbSession,
):
    """Create a new template."""
    template = Template(**template_data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    db: DbSession,
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
):
    """List all templates."""
    query = select(Template)
    if active_only:
        query = query.where(Template.is_active == True)
    
    result = await db.execute(query.offset(skip).limit(limit))
    templates = result.scalars().all()
    
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    return TemplateListResponse(templates=templates, total=total)


@router.post("/ingest", response_model=TemplateIngestionResponse)
async def ingest_template_requirements(
    source_text: Annotated[str | None, Form()] = None,
    source_file: Annotated[UploadFile | None, File()] = None,
):
    """Create an unpublished, traceable template draft from TXT/Markdown requirements."""
    try:
        provider = create_llm_provider()
    except LLMProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    service = RequirementsIngestionService(provider)
    file_bytes = await source_file.read() if source_file is not None else None
    try:
        source = service.extract_text(
            pasted_text=source_text,
            filename=source_file.filename if source_file else None,
            file_bytes=file_bytes,
            media_type=source_file.content_type if source_file else None,
        )
        template, used_fallback, warnings = await service.ingest(source)
    except RequirementsIngestionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if source_file is not None:
            await source_file.close()
    return TemplateIngestionResponse(
        template=template,
        analysis_mode="fallback" if used_fallback else "llm",
        warnings=warnings,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: DbSession,
):
    """Get a specific template by ID."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    
    return template


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    db: DbSession,
):
    """Update a template."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    db: DbSession,
):
    """Delete a template."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    
    await db.delete(template)
    await db.commit()

# Made with Bob
