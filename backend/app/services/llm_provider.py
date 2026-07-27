"""LLM provider abstraction and provider implementations."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from ..config import settings


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot complete a request."""


def _json_from_text(text: str) -> Any:
    """Extract JSON from a plain or fenced model response."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_candidates = [i for i in (cleaned.find("["), cleaned.find("{")) if i >= 0]
        if not start_candidates:
            raise LLMProviderError("The LLM returned invalid JSON")
        start = min(start_candidates)
        end = max(cleaned.rfind("]"), cleaned.rfind("}"))
        try:
            return json.loads(cleaned[start : end + 1])
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMProviderError("The LLM returned invalid JSON") from exc


class LLMProvider(ABC):
    """Common interface used by question and document services."""

    @abstractmethod
    async def _complete(self, system: str, prompt: str) -> str:
        """Generate a text completion."""

    async def generate_questions(
        self, template: dict[str, Any], context: dict[str, Any]
    ) -> list[str]:
        prompt = (
            "Create one concise, conversational interview question for every "
            "question_hints entry, in the same order. Return only a JSON array "
            "of strings.\nTemplate:\n"
            f"{json.dumps(template)}\nContext:\n{json.dumps(context)}"
        )
        value = _json_from_text(await self._complete("You design document interviews.", prompt))
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise LLMProviderError("Question response was not an array of strings")
        return value

    async def generate_followup(
        self, question: str, answer: str, context: dict[str, Any]
    ) -> str | None:
        prompt = (
            "Decide whether the answer needs one important clarification. Return "
            'only JSON in the form {"question": string|null}. Do not ask a '
            "follow-up when the answer is already specific.\n"
            f"Question: {question}\nAnswer: {answer}\nContext: {json.dumps(context)}"
        )
        value = _json_from_text(await self._complete("You conduct efficient interviews.", prompt))
        if not isinstance(value, dict):
            raise LLMProviderError("Follow-up response was not an object")
        question_value = value.get("question")
        return question_value.strip() if isinstance(question_value, str) and question_value.strip() else None

    async def review_section(
        self,
        section: dict[str, Any],
        responses: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> list[str]:
        prompt = (
            "Review this completed interview section for material gaps. Return only "
            "a JSON array containing zero, one, or at most two concise clarification "
            "questions. Consider all answers together. Do not repeat an approved "
            "question, challenge an intentional N/A/unknown answer, or request more "
            "detail when the supplied information is already sufficient.\n"
            f"Section: {json.dumps(section)}\n"
            f"Responses: {json.dumps(responses)}\n"
            f"Context: {json.dumps(context)}"
        )
        value = _json_from_text(
            await self._complete("You perform efficient section-level interview review.", prompt)
        )
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise LLMProviderError("Section review response was not an array of strings")
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))[:2]

    async def generate_document(
        self, template: dict[str, Any], responses: list[dict[str, Any]]
    ) -> str:
        prompt = (
            "Write a polished Markdown document. Follow the template section "
            "order, use only facts in the responses, and omit unanswered details. "
            "Return only Markdown.\nTemplate:\n"
            f"{json.dumps(template)}\nResponses:\n{json.dumps(responses, default=str)}"
        )
        return (await self._complete("You are a precise technical writer.", prompt)).strip()

    async def analyze_requirements(self, numbered_source: str) -> dict[str, Any]:
        """Convert requirement text into a traceable interview-template draft."""
        prompt = (
            "Analyze the numbered source below. Return only one JSON object with "
            "this exact shape: "
            '{"name":str,"description":str,"purpose":str,"audience":str,'
            '"tone":str,"category":str,"sections":[{"title":str,'
            '"description":str,"required":bool,"requirement_ids":[str],'
            '"questions":[str]}],"requirements":[{"id":str,"text":str,'
            '"required":bool,"source_lines":[int]}],"constraints":[{"type":str,'
            '"value":str,"requirement_id":str}]}. '
            "Every requirement id must look like req-001 and be used by at "
            "least one section. Source lines must point to supporting input. "
            "Do not invent rules. Use empty strings or arrays when unknown. "
            "Questions should ask the document author for content, not ask what "
            "the instructions mean.\n\nSOURCE:\n"
            f"{numbered_source}"
        )
        value = _json_from_text(
            await self._complete(
                "You extract document requirements with strict source traceability.",
                prompt,
            )
        )
        if not isinstance(value, dict):
            raise LLMProviderError("Requirements analysis was not a JSON object")
        return value


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        if not settings.openai_api_key:
            raise LLMProviderError("OPENAI_API_KEY is not configured")
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def _complete(self, system: str, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=settings.openai_temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc}") from exc


class AnthropicProvider(LLMProvider):
    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        if not settings.anthropic_api_key:
            raise LLMProviderError("ANTHROPIC_API_KEY is not configured")
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _complete(self, system: str, prompt: str) -> str:
        try:
            response = await self.client.messages.create(
                model=settings.anthropic_model,
                max_tokens=2000,
                temperature=settings.anthropic_temperature,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(block.text for block in response.content if hasattr(block, "text"))
        except Exception as exc:
            raise LLMProviderError(f"Anthropic request failed: {exc}") from exc


class OllamaProvider(LLMProvider):
    async def _complete(self, system: str, prompt: str) -> str:
        try:
            async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=90) as client:
                response = await client.post(
                    "/api/chat",
                    json={
                        "model": settings.ollama_model,
                        "stream": False,
                        "options": {"temperature": settings.ollama_temperature},
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt},
                        ],
                    },
                )
                response.raise_for_status()
                return response.json()["message"]["content"]
        except Exception as exc:
            raise LLMProviderError(f"Ollama request failed: {exc}") from exc


def create_llm_provider(provider: str | None = None) -> LLMProvider:
    """Build the configured provider without making a network request."""
    name = provider or settings.llm_default_provider
    providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
    }
    try:
        provider_type = providers[name]
    except KeyError as exc:
        raise ValueError(f"Unknown LLM provider: {name}") from exc
    return provider_type()
