"""Requirement-source extraction and traceable template drafting."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar
from uuid import uuid4

from ..config import settings
from .llm_provider import LLMProvider, LLMProviderError


class RequirementsIngestionError(ValueError):
    """Raised for unsupported or unusable requirement sources."""


@dataclass
class IngestionSource:
    text: str
    filename: str
    media_type: str


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned[:70] or "imported-document"


def _plain_markdown_text(raw: str) -> str:
    """Remove common conversion artifacts while preserving readable source text."""
    text = raw.strip()
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("\\|", "|").replace("\\_", "_").replace("\\*", "*")
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^[#>*•\-\s]+", "", text)
    text = re.sub(r"\s*\|\s*", " ", text)
    return " ".join(text.split()).strip()


def _is_table_structure(raw: str) -> bool:
    """Return true for empty Markdown cells and separator rows."""
    text = raw.strip().replace("\\|", "|")
    if not text or "|" not in text:
        return False
    cells = [cell.strip() for cell in text.strip("|").split("|")]
    return all(not cell or re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _markdown_heading(raw: str) -> str | None:
    """Recognize hash headings and short bold-only headings from converted forms."""
    stripped = raw.strip()
    if stripped.startswith("#"):
        heading = _plain_markdown_text(stripped.lstrip("#"))
        return heading or None
    if not stripped.startswith("**") or not stripped.endswith("**"):
        return None
    heading = _plain_markdown_text(stripped)
    if (
        not heading
        or len(heading) > 100
        or "?" in heading
        or re.search(r"\b(describe|explain|provide|what|how|did|was|do you)\b", heading, re.I)
    ):
        return None
    if heading.count(":") > 1:
        return None
    return heading.rstrip(":").strip() or None


def _is_meaningful_uncovered_line(raw: str) -> bool:
    text = _plain_markdown_text(raw)
    return bool(
        text
        and len(text) >= 5
        and not _is_table_structure(raw)
        and _markdown_heading(raw) is None
    )


def _requests_author_input(raw: str) -> bool:
    """Limit synthesized questions to prompts and form fields."""
    text = _plain_markdown_text(raw)
    if not text:
        return False
    if "?" in text:
        return True
    if re.match(
        r"^(describe|explain|provide|identify|list|summarize|outline|discuss|"
        r"comment on|embed|select|choose|indicate|enter|specify)\b",
        text,
        re.IGNORECASE,
    ):
        return True
    labels = [label.strip() for label in text.split(":") if label.strip()]
    return text.endswith(":") or (
        text.count(":") >= 2 and all(len(label) <= 60 for label in labels)
    )


class RequirementsIngestionService:
    allowed_suffixes: ClassVar[set[str]] = {".txt", ".md", ".markdown"}

    def __init__(self, llm_provider: LLMProvider | None):
        self.llm = llm_provider

    def extract_text(
        self,
        *,
        pasted_text: str | None,
        filename: str | None,
        file_bytes: bytes | None,
        media_type: str | None,
    ) -> IngestionSource:
        if pasted_text and pasted_text.strip():
            text = pasted_text.strip()
            source_name = filename or "pasted-requirements.txt"
            source_type = "text/plain"
        elif file_bytes is not None and filename:
            suffix = Path(filename).suffix.lower()
            if suffix not in self.allowed_suffixes:
                raise RequirementsIngestionError(
                    "Phase 3A supports TXT and Markdown files. DOCX and PDF follow next."
                )
            if len(file_bytes) > settings.max_requirements_size:
                raise RequirementsIngestionError(
                    f"Requirements file exceeds {settings.max_requirements_size} bytes"
                )
            try:
                text = file_bytes.decode("utf-8-sig").strip()
            except UnicodeDecodeError as exc:
                raise RequirementsIngestionError(
                    "Requirements files must use UTF-8 text encoding"
                ) from exc
            source_name = Path(filename).name
            source_type = media_type or "text/plain"
        else:
            raise RequirementsIngestionError(
                "Paste requirements or choose a TXT/Markdown file"
            )
        if not text:
            raise RequirementsIngestionError("The requirements source is empty")
        if len(text.encode("utf-8")) > settings.max_requirements_size:
            raise RequirementsIngestionError(
                f"Extracted text exceeds {settings.max_requirements_size} bytes"
            )
        return IngestionSource(text=text, filename=source_name, media_type=source_type)

    @staticmethod
    def _numbered(text: str) -> tuple[str, list[str]]:
        lines = text.splitlines()
        return "\n".join(f"[L{index}] {line}" for index, line in enumerate(lines, 1)), lines

    @staticmethod
    def _fallback_analysis(source: IngestionSource) -> dict[str, Any]:
        lines = source.text.splitlines()
        headings: list[tuple[int, str]] = []
        for index, raw in enumerate(lines, 1):
            stripped = raw.strip()
            if heading := _markdown_heading(raw):
                headings.append((index, heading))
            elif re.match(r"^\d+[.)]\s+\S", stripped) and len(stripped) < 100:
                headings.append((index, re.sub(r"^\d+[.)]\s+", "", stripped)))
        title = headings[0][1] if headings else Path(source.filename).stem.replace("-", " ").title()
        useful = [
            (index, _plain_markdown_text(raw))
            for index, raw in enumerate(lines, 1)
            if _is_meaningful_uncovered_line(raw)
        ]
        requirements = [
            {
                "id": f"req-{position:03d}",
                "text": text,
                "required": bool(re.search(r"\b(must|required|shall|need to)\b", text, re.IGNORECASE)),
                "source_lines": [line_number],
            }
            for position, (line_number, text) in enumerate(useful[:50], 1)
        ]
        sections = []
        usable_headings = headings
        if usable_headings:
            for heading_index, (line_number, heading) in enumerate(usable_headings):
                next_line = (
                    usable_headings[heading_index + 1][0]
                    if heading_index + 1 < len(usable_headings)
                    else len(lines) + 1
                )
                related = [
                    item for item in requirements if line_number < item["source_lines"][0] < next_line
                ]
                questions = [item["text"] for item in related if item["text"].endswith("?")]
                sections.append(
                    {
                        "title": heading,
                        "description": f"Information required for {heading}",
                        "required": True,
                        "requirement_ids": [item["id"] for item in related],
                        "questions": questions
                        or [f"What information should be included in {heading}?"],
                    }
                )
        if not sections:
            sections = [
                {
                    "title": "Document Content",
                    "description": "Content requested by the supplied requirements",
                    "required": True,
                    "requirement_ids": [item["id"] for item in requirements],
                    "questions": [
                        item["text"] for item in requirements if item["text"].endswith("?")
                    ]
                    or ["What information should this document communicate?"],
                }
            ]
        constraints = [
            {
                "type": "length" if re.search(r"\b(words?|pages?)\b", item["text"], re.IGNORECASE) else "rule",
                "value": item["text"],
                "requirement_id": item["id"],
            }
            for item in requirements
            if re.search(
                r"\b(words?|pages?|format|font|tone|audience|deadline|submit)\b",
                item["text"],
                re.IGNORECASE,
            )
        ]
        return {
            "name": title or "Imported Document",
            "description": "Document type generated from imported requirements",
            "purpose": "",
            "audience": "",
            "tone": "",
            "category": "imported",
            "sections": sections,
            "requirements": requirements,
            "constraints": constraints,
        }

    @staticmethod
    def _normalize(
        analysis: dict[str, Any], source: IngestionSource, lines: list[str]
    ) -> dict[str, Any]:
        raw_requirements = analysis.get("requirements")
        if not isinstance(raw_requirements, list) or not raw_requirements:
            raise RequirementsIngestionError("Analysis did not identify any requirements")
        requirements = []
        known_ids = set()
        for index, item in enumerate(raw_requirements[:100], 1):
            if not isinstance(item, dict) or not str(item.get("text", "")).strip():
                continue
            identifier = f"req-{index:03d}"
            source_lines = [
                number
                for number in item.get("source_lines", [])
                if isinstance(number, int) and 1 <= number <= len(lines)
            ]
            excerpt = "\n".join(lines[number - 1].strip() for number in source_lines)
            requirements.append(
                {
                    "id": identifier,
                    "text": str(item["text"]).strip(),
                    "required": bool(item.get("required", True)),
                    "source_lines": source_lines,
                    "source_excerpt": excerpt,
                }
            )
            known_ids.add(identifier)
        covered_lines = {
            number for requirement in requirements for number in requirement["source_lines"]
        }
        augmented_requirements: dict[str, tuple[int, str, bool]] = {}
        for line_number, raw_line in enumerate(lines, 1):
            text = _plain_markdown_text(raw_line)
            if (
                line_number in covered_lines
                or not _is_meaningful_uncovered_line(raw_line)
            ):
                continue
            identifier = f"req-{len(requirements) + 1:03d}"
            requirements.append(
                {
                    "id": identifier,
                    "text": text,
                    "required": bool(
                        re.search(r"\b(must|required|shall|need to)\b", text, re.IGNORECASE)
                    ),
                    "source_lines": [line_number],
                    "source_excerpt": raw_line.strip(),
                }
            )
            known_ids.add(identifier)
            augmented_requirements[identifier] = (
                line_number,
                text,
                _requests_author_input(raw_line),
            )
        sections = []
        raw_sections = analysis.get("sections")
        if not isinstance(raw_sections, list):
            raw_sections = []
        for index, item in enumerate(raw_sections[:30], 1):
            if not isinstance(item, dict) or not str(item.get("title", "")).strip():
                continue
            requested_ids = item.get("requirement_ids", [])
            mapped_ids = []
            for requested in requested_ids:
                match = re.search(r"(\d+)$", str(requested))
                if match:
                    normalized = f"req-{int(match.group(1)):03d}"
                    if normalized in known_ids:
                        mapped_ids.append(normalized)
            questions = [
                str(question).strip()
                for question in item.get("questions", [])
                if str(question).strip()
            ]
            title = str(item["title"]).strip()
            sections.append(
                {
                    "id": f"{_slug(title)}-{index}",
                    "title": title,
                    "description": str(item.get("description", "")).strip()
                    or f"Information required for {title}",
                    "required": bool(item.get("required", True)),
                    "requirement_ids": list(dict.fromkeys(mapped_ids)),
                    "question_hints": questions
                    or [f"What information should be included in {title}?"],
                }
            )
        if not sections:
            raise RequirementsIngestionError("Analysis did not identify any document sections")
        source_headings = [
            (line_number, heading)
            for line_number, raw in enumerate(lines, 1)
            if (heading := _markdown_heading(raw))
        ]
        for identifier, (line_number, text, should_ask) in augmented_requirements.items():
            heading = next(
                (
                    title
                    for heading_line, title in reversed(source_headings)
                    if heading_line < line_number
                ),
                "Document Content",
            )
            target = next(
                (
                    section
                    for section in sections
                    if _slug(section["title"]) == _slug(heading)
                ),
                None,
            )
            if target is None and not should_ask:
                sections[0]["requirement_ids"].append(identifier)
                continue
            if target is None:
                target = {
                    "id": f"{_slug(heading)}-{len(sections) + 1}",
                    "title": heading,
                    "description": f"Information required for {heading}",
                    "required": True,
                    "requirement_ids": [],
                    "question_hints": [],
                }
                sections.append(target)
            target["requirement_ids"].append(identifier)
            if should_ask:
                target["question_hints"].append(
                    text if text.endswith("?") else f"Please provide: {text.rstrip('.')}."
                )
        used_ids = {identifier for section in sections for identifier in section["requirement_ids"]}
        unassigned = known_ids - used_ids
        if unassigned:
            sections[0]["requirement_ids"].extend(sorted(unassigned))
        constraints = [
            item
            for item in analysis.get("constraints", [])
            if isinstance(item, dict) and str(item.get("value", "")).strip()
        ]
        name = str(analysis.get("name", "")).strip() or Path(source.filename).stem.title()
        return {
            "id": f"{_slug(name)}-{uuid4().hex[:6]}",
            "name": name,
            "description": str(analysis.get("description", "")).strip()
            or "Document type generated from imported requirements",
            "version": "1.0",
            "content": {
                "purpose": str(analysis.get("purpose", "")).strip(),
                "audience": str(analysis.get("audience", "")).strip(),
                "tone": str(analysis.get("tone", "")).strip(),
                "sections": sections,
                "requirements": requirements,
                "constraints": constraints,
                "source": {
                    "filename": source.filename,
                    "media_type": source.media_type,
                    "character_count": len(source.text),
                    "text": source.text,
                },
            },
            "category": str(analysis.get("category", "")).strip() or "imported",
            "estimated_duration": max(5, len(sections) * 3),
            "difficulty": "intermediate",
            "is_active": True,
        }

    async def ingest(self, source: IngestionSource) -> tuple[dict[str, Any], bool, list[str]]:
        numbered, lines = self._numbered(source.text)
        warnings: list[str] = []
        used_fallback = False
        try:
            if self.llm is None:
                raise LLMProviderError("The configured LLM provider is unavailable")
            analysis = await self.llm.analyze_requirements(numbered)
            template = self._normalize(analysis, source, lines)
        except (LLMProviderError, RequirementsIngestionError, KeyError, TypeError) as exc:
            used_fallback = True
            warnings.append(
                f"AI analysis was unavailable; a basic structural draft was created ({exc})."
            )
            analysis = self._fallback_analysis(source)
            template = self._normalize(analysis, source, lines)
        return template, used_fallback, warnings
