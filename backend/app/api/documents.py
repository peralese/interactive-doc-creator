"""Document generation API endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import get_db
from ..models.session import Session
from ..services.document_gen import DocumentGenerator, DocumentVersions
from ..services.llm_provider import LLMProviderError, create_llm_provider

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


class DocumentGenerateRequest(BaseModel):
    """Request schema for document generation."""
    session_id: UUID
    format: Literal["markdown", "pdf", "docx", "html"] = "markdown"


class DocumentResponse(BaseModel):
    """Both versions of a session's document.

    ``content`` is the version the call produced (the refined text for /generate,
    the rough draft for /preview).
    """
    content: str
    format: str
    session_id: UUID
    draft: str
    refined: str | None = None
    refined_stale: bool = False


def _document_response(
    session_id: UUID, versions: DocumentVersions, content: str, format: str = "markdown"
) -> DocumentResponse:
    return DocumentResponse(
        content=content,
        format=format,
        session_id=session_id,
        draft=versions.draft,
        refined=versions.refined,
        refined_stale=versions.refined_stale,
    )


@router.post("/generate", response_model=DocumentResponse)
async def generate_document(
    request: DocumentGenerateRequest, db: DbSession
):
    """Refine the session's answers with the LLM; the rough draft is kept alongside."""
    generator = DocumentGenerator(db, create_llm_provider())
    try:
        versions = await generator.generate(request.session_id)
        content = versions.refined or ""
        if request.format != "markdown":
            await generator.export(content, request.format)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(
            status_code=503,
            detail="AI refinement is unavailable right now. Your rough draft and any earlier refined version are unchanged.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return _document_response(request.session_id, versions, content, request.format)


@router.get("/download/{session_id}")
async def download_document(
    session_id: UUID,
    db: DbSession,
    format: Literal["markdown", "pdf", "docx", "html"] = "markdown",
    version: Literal["draft", "refined"] | None = None,
):
    """Download the rough draft or the refined document (default: refined if it exists)."""
    generator = DocumentGenerator(db, create_llm_provider())
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    try:
        versions = await generator.preview(session_id)
        if version is None:
            version = "refined" if versions.refined else "draft"
        if version == "refined" and not versions.refined:
            raise HTTPException(status_code=404, detail="This document has not been refined yet")
        content = versions.refined if version == "refined" else versions.draft
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
            "Content-Disposition": f'attachment; filename="document-{session_id}-{version}.{extensions[format]}"'
        },
    )


@router.get("/preview/{session_id}", response_model=DocumentResponse)
async def preview_document(
    session_id: UUID, db: DbSession
):
    """Preview the current state of the document."""
    try:
        versions = await DocumentGenerator(
            db, create_llm_provider()
        ).preview(session_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _document_response(session_id, versions, versions.draft)

# Made with Bob
