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


def _is_closed_short_answer(question: str, answer: str) -> bool:
    return len(answer.split()) <= 3 and bool(
        re.match(
            r"^(do|does|did|is|are|was|were|can|could|will|would|have|has)\b",
            question.strip(),
            re.IGNORECASE,
        )
    )


class QuestionGenerator:
    def __init__(self, db: AsyncSession, llm_provider: LLMProvider | None):
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
        return [
            {
                "question": question,
                "section_id": section_id,
                "sequence_number": index,
                "is_followup": False,
            }
            for index, (section_id, question) in enumerate(hints)
        ]

    async def generate_followup_question(
        self, question: str, answer: str, context: dict[str, Any] | None = None
    ) -> str | None:
        if self.llm is None:
            return None
        if _is_intentional_terminal_answer(answer) or _is_basic_field_question(question):
            return None
        if len(answer.split()) < 3:
            return "Could you add a little more detail?"
        try:
            return await self.llm.generate_followup(question, answer, context or {})
        except LLMProviderError as exc:
            logger.warning("Skipping optional follow-up because LLM is unavailable: %s", exc)
            return None

    async def review_section(
        self,
        section: dict[str, Any],
        responses: list[dict[str, Any]],
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        if self.llm is None or not responses:
            return []
        if not any(
            not _is_basic_field_question(str(item.get("question", "")))
            and not _is_intentional_terminal_answer(str(item.get("answer", "")))
            and not _is_closed_short_answer(
                str(item.get("question", "")),
                str(item.get("answer", "")),
            )
            for item in responses
        ):
            return []
        return await self.llm.review_section(section, responses, context or {})
