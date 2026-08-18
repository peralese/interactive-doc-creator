"""Capture service — LLM-powered polish for free-flow transcriptions."""

from __future__ import annotations

import logging

from .llm_provider import LLMProviderError, _json_from_text, create_llm_provider

logger = logging.getLogger(__name__)

_POLISH_SYSTEM = (
    "You are a clear, concise writing assistant. "
    "You help people refine raw spoken ideas into polished written form. "
    "You always respond with a single valid JSON object and nothing else."
)

_POLISH_PROMPT = """\
The following is a raw, unedited voice transcription of a free-flow idea. \
It may contain filler words, run-on sentences, and incomplete thoughts.

Respond with ONLY a single JSON object — no code fences, no explanation, no text before or after.
Use \\n to represent newlines inside string values (do NOT use literal line breaks inside strings).

The JSON must have exactly these two keys:
- "clean_prose": A polished prose version preserving the speaker's voice. Fix grammar, \
remove filler words. Do not add facts not in the original.
- "structured_breakdown": A structured breakdown using \\n for line breaks — include a \
short title line, a one-sentence summary line, then bullet points starting with "- ".

Example format (do not copy this content, only the structure):
{{"clean_prose": "The speaker described an idea for improving X.", "structured_breakdown": "Title\\n\\nSummary sentence.\\n\\n- Point one\\n- Point two"}}

RAW TRANSCRIPTION:
{raw_text}
"""


class CaptureService:
    """Service for polishing capture transcriptions via an LLM."""

    async def polish(self, raw_text: str, provider: str = "ollama") -> dict:
        """Polish raw transcription text into clean prose and a structured breakdown.

        Args:
            raw_text: The raw transcription to polish.
            provider: LLM provider name — 'ollama' keeps data local, 'openai' uses cloud.

        Returns:
            dict with 'clean_prose' and 'structured_breakdown' keys.

        Raises:
            LLMProviderError: If the LLM call fails or returns invalid JSON.
        """
        llm = create_llm_provider(provider)
        prompt = _POLISH_PROMPT.format(raw_text=raw_text)
        raw_response = await llm._complete(_POLISH_SYSTEM, prompt)

        result = _json_from_text(raw_response)

        if not isinstance(result, dict):
            raise LLMProviderError("Polish response was not a JSON object")

        clean_prose = str(result.get("clean_prose", "")).strip()
        structured_breakdown = str(result.get("structured_breakdown", "")).strip()

        if not clean_prose and not structured_breakdown:
            raise LLMProviderError("Polish response missing required keys")

        # Normalise escaped newlines that some models return as literal \\n
        clean_prose = clean_prose.replace("\\n", "\n")
        structured_breakdown = structured_breakdown.replace("\\n", "\n")

        return {
            "clean_prose": clean_prose,
            "structured_breakdown": structured_breakdown,
        }

# Made with Bob
