"""Document synthesis and export."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.response import Response
from ..models.session import Session
from ..models.template import Template
from .llm_provider import LLMProvider, LLMProviderError


@dataclass
class DocumentVersions:
    draft: str
    refined: str | None
    refined_stale: bool


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

    @staticmethod
    def _versions(session: Session) -> DocumentVersions:
        return DocumentVersions(
            draft=session.generated_document or "",
            refined=session.refined_document,
            refined_stale=bool(session.refined_document and session.refined_stale),
        )

    def _ensure_draft(self, session: Session, template: Template, responses: list[Response]) -> None:
        draft = self._fallback_markdown(template, responses)
        cached = session.generated_document
        # Before refined_document existed, "Refine with AI" overwrote the draft cache.
        # A cached document that isn't the deterministic draft is that refined text.
        if cached and cached != draft and not session.refined_document:
            session.refined_document = cached
            session.refined_stale = False
        session.generated_document = draft

    async def generate(self, session_id: UUID) -> DocumentVersions:
        """Refine the answers with the LLM, keeping the rough draft untouched.

        Raises LLMProviderError if refinement fails; both stored versions are left as-is.
        """
        session, template, responses = await self._load(session_id)
        self._ensure_draft(session, template, responses)
        response_data = [
            {
                "section_id": response.section_id,
                "question": response.question,
                "answer": response.answer,
                "is_followup": response.is_followup,
            }
            for response in responses
        ]
        output_type = session.output_type or "report"
        try:
            refined = await self.llm.generate_document(
                template.content, response_data, output_type=output_type
            )
        except LLMProviderError:
            await self.db.commit()  # keep the rebuilt draft
            raise
        session.refined_document = refined
        session.refined_stale = False
        await self.db.commit()
        return self._versions(session)

    async def preview(self, session_id: UUID) -> DocumentVersions:
        """Return the rough draft (rebuilt without the LLM if needed) and any refined version."""
        session, template, responses = await self._load(session_id)
        self._ensure_draft(session, template, responses)
        await self.db.commit()  # no-op unless the draft or legacy refined text changed
        return self._versions(session)

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
