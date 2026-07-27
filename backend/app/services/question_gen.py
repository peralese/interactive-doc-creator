"""Question generation and interview progress logic."""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.template import Template
from .llm_provider import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

TERMINAL_ANSWER_PATTERNS = (
    r"n/?a",
    r"not applicable",
    r"none",
    r"unknown",
    r"unsure",
    r"tbd",
    r"to be determined",
    r"(?:i )?(?:do not|don't) know",
    r"(?:i )?(?:do not|don't|currently don't) have (?:one|this|that|a .+)",
    r"not yet",
    r"prefer not to (?:say|answer|provide)",
)

BASIC_FIELD_TERMS = (
    "name",
    "email",
    "approval date",
    "start date",
    "end date",
    "location",
    "employer",
    "your role",
    "phone",
    "address",
)


def _normalized_answer(answer: str) -> str:
    return re.sub(r"[.!?]+$", "", " ".join(answer.lower().split())).strip()


def _is_intentional_terminal_answer(answer: str) -> bool:
    normalized = _normalized_answer(answer)
    return any(re.fullmatch(pattern, normalized) for pattern in TERMINAL_ANSWER_PATTERNS)


def _is_basic_field_question(question: str) -> bool:
    normalized = " ".join(question.lower().split())
    return any(term in normalized for term in BASIC_FIELD_TERMS)


class QuestionGenerator:
    def __init__(self, db: AsyncSession, llm_provider: LLMProvider):
        self.db = db
        self.llm = llm_provider

    async def load_template(self, template_id: str) -> Template:
        result = await self.db.execute(select(Template).where(Template.id == template_id))
        template = result.scalar_one_or_none()
        if template is None:
            raise LookupError(f"Template {template_id} not found")
        return template

    async def generate_initial_questions(
        self, template_id: str, context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        template = await self.load_template(template_id)
        sections = template.content.get("sections", [])
        hints = [
            (section["id"], hint)
            for section in sections
            for hint in section.get("question_hints", [])
        ]
        generated: list[str] = []
        try:
            generated = await self.llm.generate_questions(template.content, context or {})
        except LLMProviderError as exc:
            logger.warning("Using template questions because LLM is unavailable: %s", exc)
        if len(generated) != len(hints):
            generated = [hint for _, hint in hints]
        return [
            {
                "question": question,
                "section_id": section_id,
                "sequence_number": index,
                "is_followup": False,
            }
            for index, ((section_id, _), question) in enumerate(zip(hints, generated))
        ]

    async def generate_followup_question(
        self, question: str, answer: str, context: dict[str, Any] | None = None
    ) -> str | None:
        if _is_intentional_terminal_answer(answer) or _is_basic_field_question(question):
            return None
        if len(answer.split()) < 3:
            return "Could you add a little more detail?"
        try:
            return await self.llm.generate_followup(question, answer, context or {})
        except LLMProviderError as exc:
            logger.warning("Skipping optional follow-up because LLM is unavailable: %s", exc)
            return None
