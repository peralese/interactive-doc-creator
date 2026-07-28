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


def _canonical_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _is_suspicious_question(value: str) -> bool:
    text = _canonical_text(value)
    return any(
        phrase in text
        for phrase in (
            "what content belongs in this table cell",
            "what table separator",
            "what table structure",
            "what is the section title",
            "what is the document title",
        )
    )


def _is_generic_question(value: str) -> bool:
    text = _canonical_text(value)
    return text.startswith(
        (
            "what information should be included in",
            "what information is required for",
            "please provide information for",
        )
    )


def _content_type(raw: str) -> str:
    text = _plain_markdown_text(raw)
    if _markdown_heading(raw):
        return "heading"
    if re.search(r"\b(yes\s*/\s*no|choose one|check one|select)\b", text, re.I):
        return "choice"
    if _requests_author_input(raw):
        return "narrative_prompt" if "?" in text or len(text) > 80 else "form_field"
    if re.search(r"\b(words?|pages?|format|font|tone|deadline|submit)\b", text, re.I):
        return "constraint"
    if re.search(r"https?://|\brefer to\b", raw, re.I):
        return "reference"
    return "instruction"


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
        analysis_warnings: list[str] = []
        raw_requirements = analysis.get("requirements")
        if not isinstance(raw_requirements, list) or not raw_requirements:
            raise RequirementsIngestionError("Analysis did not identify any requirements")
        requirements = []
        known_ids = set()
        source_id_map: dict[str, str] = {}
        requirement_by_text: dict[str, dict[str, Any]] = {}
        for index, item in enumerate(raw_requirements[:100], 1):
            if not isinstance(item, dict) or not str(item.get("text", "")).strip():
                continue
            source_lines = [
                number
                for number in item.get("source_lines", [])
                if isinstance(number, int) and 1 <= number <= len(lines)
            ]
            original_id = str(item.get("id", f"req-{index:03d}"))
            if not source_lines:
                analysis_warnings.append(
                    f"Ignored an untraceable requirement: {str(item['text']).strip()}"
                )
                continue
            canonical = _canonical_text(str(item["text"]))
            if canonical in requirement_by_text:
                existing = requirement_by_text[canonical]
                source_id_map[original_id] = existing["id"]
                existing["source_lines"] = sorted(
                    set(existing["source_lines"]) | set(source_lines)
                )
                existing["source_excerpt"] = "\n".join(
                    lines[number - 1].strip() for number in existing["source_lines"]
                )
                if existing["required"] != bool(item.get("required", True)):
                    analysis_warnings.append(
                        f"Requirement appears both required and optional: {item['text']}"
                    )
                else:
                    analysis_warnings.append(
                        f"Merged duplicate requirement: {str(item['text']).strip()}"
                    )
                continue
            identifier = f"req-{len(requirements) + 1:03d}"
            excerpt = "\n".join(lines[number - 1].strip() for number in source_lines)
            requirement = {
                "id": identifier,
                "text": str(item["text"]).strip(),
                "required": bool(item.get("required", True)),
                "source_lines": source_lines,
                "source_excerpt": excerpt,
                "content_type": str(item.get("content_type", "")).strip()
                or _content_type(lines[source_lines[0] - 1]),
                "confidence": str(item.get("confidence", "")).strip() or "medium",
            }
            if requirement["confidence"] == "low":
                analysis_warnings.append(
                    f"Review low-confidence requirement: {requirement['text']}"
                )
            requirements.append(requirement)
            requirement_by_text[canonical] = requirement
            source_id_map[original_id] = identifier
            known_ids.add(identifier)
        if not requirements:
            raise RequirementsIngestionError(
                "Analysis did not identify any traceable requirements"
            )
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
                    "content_type": _content_type(raw_line),
                    "confidence": "high",
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
                normalized = source_id_map.get(str(requested))
                if normalized is None:
                    match = re.search(r"(\d+)$", str(requested))
                    if match:
                        normalized = source_id_map.get(
                            f"req-{int(match.group(1)):03d}"
                        )
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
        seen_questions: set[str] = set()
        retained_question_count = 0
        maximum_questions = 200
        for section in sections:
            cleaned_questions = []
            section_questions = section["question_hints"]
            for question in section_questions:
                canonical = _canonical_text(question)
                if not canonical or _is_suspicious_question(question):
                    analysis_warnings.append(
                        f"Removed suspicious generated question: {question}"
                    )
                    continue
                if canonical in seen_questions:
                    analysis_warnings.append(
                        f"Removed duplicate generated question: {question}"
                    )
                    continue
                if _is_generic_question(question) and len(section_questions) > 1:
                    analysis_warnings.append(
                        f"Removed generic generated question: {question}"
                    )
                    continue
                if _is_generic_question(question):
                    analysis_warnings.append(
                        f"Review this generic generated question: {question}"
                    )
                if retained_question_count >= maximum_questions:
                    analysis_warnings.append(
                        f"Question list was limited to {maximum_questions} questions."
                    )
                    continue
                seen_questions.add(canonical)
                cleaned_questions.append(question)
                retained_question_count += 1
            section["question_hints"] = cleaned_questions
        sections = [
            section
            for section in sections
            if section["requirement_ids"] or section["question_hints"]
        ]
        if not sections:
            raise RequirementsIngestionError(
                "Analysis did not produce any usable interview sections"
            )
        constraints = [
            item
            for item in analysis.get("constraints", [])
            if isinstance(item, dict) and str(item.get("value", "")).strip()
        ]
        constraint_values: dict[str, set[str]] = {}
        for constraint in constraints:
            kind = _canonical_text(str(constraint.get("type", "")))
            constraint_values.setdefault(kind, set()).add(
                _canonical_text(str(constraint["value"]))
            )
        for kind, values in constraint_values.items():
            if kind in {"length", "word count", "page count", "tone"} and len(values) > 1:
                analysis_warnings.append(
                    f"Review potentially conflicting {kind} constraints."
                )
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
                "analysis_warnings": list(dict.fromkeys(analysis_warnings)),
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
        warnings.extend(template["content"].get("analysis_warnings", []))
        return template, used_fallback, warnings
