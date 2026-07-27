"""Document generation API endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import get_db
from ..models.session import Session
from ..services.document_gen import DocumentGenerator
from ..services.llm_provider import create_llm_provider

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


class DocumentGenerateRequest(BaseModel):
    """Request schema for document generation."""
    session_id: UUID
    format: Literal["markdown", "pdf", "docx", "html"] = "markdown"


class DocumentResponse(BaseModel):
    """Response schema for generated document."""
    content: str
    format: str
    session_id: UUID


@router.post("/generate", response_model=DocumentResponse)
async def generate_document(
    request: DocumentGenerateRequest, db: DbSession
):
    """Generate a document from session responses."""
    generator = DocumentGenerator(db, create_llm_provider())
    try:
        content = await generator.generate(request.session_id)
        if request.format != "markdown":
            await generator.export(content, request.format)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return DocumentResponse(content=content, format=request.format, session_id=request.session_id)


@router.get("/download/{session_id}")
async def download_document(
    session_id: UUID,
    db: DbSession,
    format: Literal["markdown", "pdf", "docx", "html"] = "markdown",
):
    """Download generated document in specified format."""
    generator = DocumentGenerator(db, create_llm_provider())
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    try:
        content = session.generated_document or await generator.generate(session_id)
        body, media_type = await generator.export(content, format)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    extensions = {"markdown": "md", "html": "html", "docx": "docx", "pdf": "pdf"}
    return Response(
        content=body,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="document-{session_id}.{extensions[format]}"'
        },
    )


@router.get("/preview/{session_id}", response_model=DocumentResponse)
async def preview_document(
    session_id: UUID, db: DbSession
):
    """Preview the current state of the document."""
    try:
        content = await DocumentGenerator(
            db, create_llm_provider()
        ).preview(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return DocumentResponse(content=content, format="markdown", session_id=session_id)

# Made with Bob
