"""Question generation API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import get_db
from ..models.response import Response
from ..models.session import Session
from ..services.llm_provider import LLMProviderError, create_llm_provider
from ..services.question_gen import QuestionGenerator

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


class QuestionRequest(BaseModel):
    """Request schema for generating questions."""
    session_id: UUID
    template_id: str


class QuestionResponse(BaseModel):
    """Response schema for generated questions."""
    question: str
    section_id: str
    sequence_number: int
    is_followup: bool = False
    parent_response_id: UUID | None = None


class FollowupRequest(BaseModel):
    """Request schema for generating follow-up questions."""
    session_id: UUID
    response_id: UUID
    answer: str


@router.post("/generate", response_model=list[QuestionResponse])
async def generate_questions(
    request: QuestionRequest, db: DbSession
):
    """Generate initial questions from template."""
    session = await db.get(Session, request.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {request.session_id} not found")
    if session.template_id != request.template_id:
        raise HTTPException(status_code=400, detail="Template does not match the session")
    try:
        return await QuestionGenerator(db, create_llm_provider()).generate_initial_questions(
            request.template_id, {"session_id": str(request.session_id)}
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/followup", response_model=QuestionResponse | None)
async def generate_followup(
    request: FollowupRequest, db: DbSession
):
    """Generate a follow-up question based on the answer."""
    response = await db.get(Response, request.response_id)
    if response is None or response.session_id != request.session_id:
        raise HTTPException(status_code=404, detail="Response not found in this session")
    if response.is_followup:
        return None
    question = await QuestionGenerator(
        db, create_llm_provider()
    ).generate_followup_question(
        response.question,
        request.answer,
        {"section_id": response.section_id},
    )
    if question is None:
        return None
    sequence_result = await db.execute(
        select(func.max(Response.sequence_number)).where(
            Response.session_id == request.session_id
        )
    )
    sequence_number = (sequence_result.scalar_one_or_none() or 0) + 1
    return QuestionResponse(
        question=question,
        section_id=response.section_id,
        sequence_number=sequence_number,
        is_followup=True,
        parent_response_id=response.id,
    )


@router.get("/next/{session_id}", response_model=QuestionResponse | None)
async def get_next_question(
    session_id: UUID, db: DbSession
):
    """Get the next question for a session."""
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    questions = await QuestionGenerator(
        db, create_llm_provider()
    ).generate_initial_questions(session.template_id, {"session_id": str(session_id)})
    result = await db.execute(
        select(Response.sequence_number).where(
            Response.session_id == session_id, Response.is_followup.is_(False)
        )
    )
    answered = set(result.scalars())
    return next(
        (question for question in questions if question["sequence_number"] not in answered),
        None,
    )

# Made with Bob
