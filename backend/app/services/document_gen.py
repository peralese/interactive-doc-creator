"""Document synthesis and export."""

from __future__ import annotations

from io import BytesIO
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.response import Response
from ..models.session import Session
from ..models.template import Template
from .llm_provider import LLMProvider, LLMProviderError


class DocumentGenerator:
    def __init__(self, db: AsyncSession, llm_provider: LLMProvider):
        self.db = db
        self.llm = llm_provider

    async def _load(self, session_id: UUID) -> tuple[Session, Template, list[Response]]:
        session = await self.db.get(Session, session_id)
        if session is None:
            raise LookupError(f"Session {session_id} not found")
        template = await self.db.get(Template, session.template_id)
        if template is None:
            raise LookupError(f"Template {session.template_id} not found")
        result = await self.db.execute(
            select(Response)
            .where(Response.session_id == session_id)
            .order_by(Response.sequence_number, Response.created_at)
        )
        return session, template, list(result.scalars())

    @staticmethod
    def _fallback_markdown(template: Template, responses: list[Response]) -> str:
        by_section: dict[str, list[Response]] = {}
        for response in responses:
            by_section.setdefault(response.section_id, []).append(response)
        lines = [f"# {template.name}", ""]
        if template.description:
            lines.extend([template.description, ""])
        for section in template.content.get("sections", []):
            entries = by_section.get(section["id"], [])
            if not entries:
                continue
            lines.extend([f"## {section['title']}", ""])
            for entry in entries:
                lines.extend([f"**{entry.question}**", "", entry.answer.strip(), ""])
        return "\n".join(lines).strip() + "\n"

    async def generate(self, session_id: UUID) -> str:
        session, template, responses = await self._load(session_id)
        response_data = [
            {
                "section_id": response.section_id,
                "question": response.question,
                "answer": response.answer,
                "is_followup": response.is_followup,
            }
            for response in responses
        ]
        try:
            content = await self.llm.generate_document(template.content, response_data)
        except LLMProviderError:
            content = self._fallback_markdown(template, responses)
        session.generated_document = content
        await self.db.commit()
        return content

    async def preview(self, session_id: UUID) -> str:
        _, template, responses = await self._load(session_id)
        return self._fallback_markdown(template, responses)

    async def export(self, content: str, format: str) -> tuple[bytes, str]:
        if format == "markdown":
            return content.encode(), "text/markdown; charset=utf-8"
        if format == "html":
            import markdown

            html = markdown.markdown(content, extensions=["tables", "fenced_code"])
            return html.encode(), "text/html; charset=utf-8"
        if format == "docx":
            from docx import Document

            document = Document()
            for line in content.splitlines():
                if line.startswith("# "):
                    document.add_heading(line[2:], 0)
                elif line.startswith("## "):
                    document.add_heading(line[3:], 1)
                elif line.strip():
                    document.add_paragraph(line.replace("**", ""))
            output = BytesIO()
            document.save(output)
            return output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "pdf":
            try:
                import markdown
                from weasyprint import HTML
            except ImportError as exc:
                raise RuntimeError("PDF export is optional; install requirements-pdf.txt") from exc
            return HTML(string=markdown.markdown(content)).write_pdf(), "application/pdf"
        raise ValueError(f"Unsupported export format: {format}")
