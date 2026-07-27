"""Phase 2 service and API integration tests."""

import json
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from app.api import documents, questions, templates, transcriptions
from app.config import settings
from app.main import app
from app.models.base import Base, get_db
from app.services.llm_provider import LLMProvider
from app.services.question_gen import QuestionGenerator
from app.services.requirements_ingestion import IngestionSource, RequirementsIngestionService


class StubProvider(LLMProvider):
    async def _complete(self, system: str, prompt: str) -> str:
        if "Analyze the numbered source" in prompt:
            return json.dumps(
                {
                    "name": "Tool Description",
                    "description": "Describe a software tool for reviewers.",
                    "purpose": "Explain the tool and its value.",
                    "audience": "Technical reviewers",
                    "tone": "Clear and concise",
                    "category": "technical",
                    "requirements": [
                        {
                            "id": "req-001",
                            "text": "The document must be under 800 words.",
                            "required": True,
                            "source_lines": [4],
                        },
                    ],
                    "sections": [
                        {
                            "title": "Problem",
                            "description": "Problem addressed by the tool",
                            "required": True,
                            "requirement_ids": ["req-001"],
                            "questions": ["How should the length rule be applied?"],
                        },
                    ],
                    "constraints": [
                        {
                            "type": "length",
                            "value": "Under 800 words",
                            "requirement_id": "req-001",
                        }
                    ],
                }
            )
        if "one concise" in prompt:
            template = json.loads(prompt.split("Template:\n", 1)[1].split("\nContext:", 1)[0])
            hints = [
                hint
                for section in template["sections"]
                for hint in section.get("question_hints", [])
            ]
            return json.dumps([f"Please explain: {hint}" for hint in hints])
        if "Review this completed interview section" in prompt:
            return json.dumps(
                [
                    "What measurable result did the client observe?",
                    "How was that result validated?",
                    "This third question must be discarded.",
                ]
            )
        if "clarification" in prompt:
            return '{"question": null}'
        return "# Generated Project\n\nA synthesized result."


class StubSpeechService:
    async def transcribe(self, audio_file_path: str):
        assert Path(audio_file_path).read_bytes() == b"fake audio"
        return {"text": "A clear answer.", "confidence": 0.93, "language": "en"}

    async def transcribe_stream(self, audio_stream):
        content = b""
        async for chunk in audio_stream:
            content += chunk
        assert content == b"chunk onechunk two"
        yield "A streamed answer."


class FollowupProvider(LLMProvider):
    def __init__(self):
        self.calls = 0

    async def _complete(self, system: str, prompt: str) -> str:
        self.calls += 1
        return '{"question": "What specific outcome did that produce?"}'


@pytest_asyncio.fixture
async def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def test_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[transcriptions.get_speech_service] = lambda: StubSpeechService()
    monkeypatch.setattr(questions, "create_llm_provider", lambda: StubProvider())
    monkeypatch.setattr(documents, "create_llm_provider", lambda: StubProvider())
    monkeypatch.setattr(templates, "create_llm_provider", lambda: StubProvider())
    monkeypatch.setattr(settings, "audio_storage_path", str(tmp_path / "audio"))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_interview_to_document_flow(client):
    template = {
        "id": "test-template",
        "name": "Test Project",
        "description": "A test template",
        "content": {
            "sections": [
                {
                    "id": "purpose",
                    "title": "Purpose",
                    "description": "Why",
                    "question_hints": ["What problem is solved?"],
                }
            ]
        },
    }
    assert (await client.post("/api/templates/", json=template)).status_code == 201
    session_response = await client.post(
        "/api/sessions/", json={"template_id": "test-template", "metadata": {"owner": "Ada"}}
    )
    assert session_response.status_code == 201
    assert session_response.json()["metadata"] == {"owner": "Ada"}
    session_id = session_response.json()["id"]

    generated = await client.post(
        "/api/questions/generate",
        json={"session_id": session_id, "template_id": "test-template"},
    )
    assert generated.status_code == 200
    question = generated.json()[0]
    assert question["section_id"] == "purpose"
    assert question["question"] == "What problem is solved?"

    answer = await client.post(
        "/api/responses/",
        json={
            "session_id": session_id,
            "section_id": question["section_id"],
            "question": question["question"],
            "answer": "It eliminates repetitive manual document assembly.",
            "sequence_number": question["sequence_number"],
        },
    )
    assert answer.status_code == 201
    assert (await client.get(f"/api/questions/next/{session_id}")).json() is None
    resumed = await client.get(f"/api/sessions/{session_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["current_question_index"] == 1
    assert len(resumed.json()["responses"]) == 1

    autosaved = await client.post(
        f"/api/sessions/{session_id}/autosave",
        json={"metadata": {"owner": "Ada", "draft": True}},
    )
    assert autosaved.status_code == 200
    assert autosaved.json()["metadata"]["draft"] is True

    preview = await client.get(f"/api/documents/preview/{session_id}")
    assert "manual document assembly" in preview.json()["content"]

    generated_document = await client.post(
        "/api/documents/generate", json={"session_id": session_id, "format": "markdown"}
    )
    assert generated_document.status_code == 200
    assert "# Generated Project" in generated_document.json()["content"]

    html = await client.get(f"/api/documents/download/{session_id}?format=html")
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")


@pytest.mark.asyncio
async def test_missing_resources_return_404(client):
    missing = uuid4()
    assert (await client.get(f"/api/questions/next/{missing}")).status_code == 404
    assert (await client.get(f"/api/documents/preview/{missing}")).status_code == 404


@pytest.mark.asyncio
async def test_followup_policy_accepts_terminal_and_basic_field_answers():
    provider = FollowupProvider()
    generator = QuestionGenerator(None, provider)

    assert (
        await generator.generate_followup_question(
            "What are the certifying mentor's name and approval date?",
            "I currently don't have a mentor.",
        )
        is None
    )
    assert (
        await generator.generate_followup_question(
            "Describe the optional diagram you will provide.",
            "N/A",
        )
        is None
    )
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_narrative_answer_can_receive_one_model_followup():
    provider = FollowupProvider()
    generator = QuestionGenerator(None, provider)

    followup = await generator.generate_followup_question(
        "Describe the business outcome you produced.",
        "We improved the delivery process for the client.",
    )

    assert followup == "What specific outcome did that produce?"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_basic_section_does_not_call_model_for_review():
    provider = FollowupProvider()
    generator = QuestionGenerator(None, provider)

    questions = await generator.review_section(
        {"id": "personal-information"},
        [
            {"question": "What is the applicant's name?", "answer": "Erick Perales"},
            {"question": "Do you have mentor approval?", "answer": "Not yet"},
        ],
    )

    assert questions == []
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_followup_response_does_not_generate_another_followup(client):
    template = {
        "id": "bounded-followup-template",
        "name": "Bounded follow-up",
        "description": "Tests follow-up depth",
        "content": {
            "sections": [
                {
                    "id": "outcome",
                    "title": "Outcome",
                    "question_hints": ["Describe the outcome."],
                }
            ]
        },
    }
    assert (await client.post("/api/templates/", json=template)).status_code == 201
    session = await client.post(
        "/api/sessions/",
        json={"template_id": template["id"], "metadata": {}},
    )
    session_id = session.json()["id"]
    saved = await client.post(
        "/api/responses/",
        json={
            "session_id": session_id,
            "section_id": "outcome",
            "question": "Could you quantify that outcome?",
            "answer": "It reduced processing time by 25 percent.",
            "sequence_number": 1,
            "is_followup": True,
        },
    )
    response = await client.post(
        "/api/questions/followup",
        json={
            "session_id": session_id,
            "response_id": saved.json()["id"],
            "answer": saved.json()["answer"],
        },
    )

    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_section_review_is_bounded_and_persisted(client):
    template = {
        "id": "section-review-template",
        "name": "Section review",
        "description": "Tests batched clarification",
        "content": {
            "sections": [
                {
                    "id": "outcome",
                    "title": "Outcome",
                    "question_hints": [
                        "What outcome did the project produce?",
                        "Who benefited from the outcome?",
                    ],
                }
            ]
        },
    }
    assert (await client.post("/api/templates/", json=template)).status_code == 201
    session = await client.post(
        "/api/sessions/",
        json={"template_id": template["id"], "metadata": {}},
    )
    session_id = session.json()["id"]
    for sequence, (question, answer) in enumerate(
        [
            ("What outcome did the project produce?", "Delivery became faster."),
            ("Who benefited from the outcome?", "The client operations team benefited."),
        ]
    ):
        saved = await client.post(
            "/api/responses/",
            json={
                "session_id": session_id,
                "section_id": "outcome",
                "question": question,
                "answer": answer,
                "sequence_number": sequence,
            },
        )
        assert saved.status_code == 201

    first = await client.post(
        "/api/questions/section-review",
        json={"session_id": session_id, "section_id": "outcome"},
    )
    second = await client.post(
        "/api/questions/section-review",
        json={"session_id": session_id, "section_id": "outcome"},
    )

    assert first.status_code == 200
    assert len(first.json()) == 2
    assert second.json() == first.json()
    resumed = await client.get(f"/api/sessions/{session_id}/resume")
    assert resumed.json()["metadata"]["section_reviews"]["outcome"] == first.json()


@pytest.mark.asyncio
async def test_audio_upload_transcription(client):
    session_id = uuid4()
    response = await client.post(
        "/api/transcriptions/",
        data={"session_id": str(session_id)},
        files={"audio": ("answer.webm", b"fake audio", "audio/webm")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == "A clear answer."
    assert body["confidence"] == 0.93
    assert body["session_id"] == str(session_id)
    assert Path(body["audio_path"]).is_file()


def test_audio_websocket_protocol(monkeypatch):
    monkeypatch.setattr(
        transcriptions, "get_speech_service", lambda: StubSpeechService()
    )
    with (
        TestClient(app) as sync_client,
        sync_client.websocket_connect("/api/transcriptions/stream") as websocket,
    ):
        assert websocket.receive_json() == {"event": "ready"}
        websocket.send_bytes(b"chunk one")
        websocket.send_bytes(b"chunk two")
        websocket.send_text("stop")
        assert websocket.receive_json() == {"event": "transcribing"}
        assert websocket.receive_json() == {
            "event": "result",
            "text": "A streamed answer.",
        }


@pytest.mark.asyncio
async def test_requirements_ingestion_to_saved_template(client):
    source = """# Tool Description
Explain the problem the tool solves.
# Rules
The document must be under 800 words.
"""
    analysis = await client.post(
        "/api/templates/ingest",
        data={"source_text": source},
    )
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["analysis_mode"] == "llm"
    assert body["template"]["name"] == "Tool Description"
    assert len(body["template"]["content"]["requirements"]) == 2
    assert body["template"]["content"]["requirements"][0]["source_excerpt"]
    assert body["template"]["content"]["sections"][0]["requirement_ids"] == ["req-001"]
    assert any(
        section["title"] == "Tool Description"
        and section["requirement_ids"] == ["req-002"]
        for section in body["template"]["content"]["sections"]
    )

    saved = await client.post("/api/templates/", json=body["template"])
    assert saved.status_code == 201
    assert saved.json()["content"]["source"]["text"] == source.strip()


@pytest.mark.asyncio
async def test_requirements_ingestion_rejects_unsupported_file(client):
    response = await client.post(
        "/api/templates/ingest",
        files={"source_file": ("rules.pdf", b"%PDF", "application/pdf")},
    )
    assert response.status_code == 400
    assert "TXT and Markdown" in response.json()["detail"]


def test_markdown_table_artifacts_do_not_become_interview_questions():
    source = IngestionSource(
        filename="architect-profile.md",
        media_type="text/markdown",
        text="""| **Architect Project Profile** | | --- | --- |
| --- |
**Personal Information:**
**Applicant Name:** **Applicant Email:**
**Describe the business outcome you produced?**
|   |
| --- |""",
    )
    lines = source.text.splitlines()
    analysis = {
        "name": "Architect Project Profile",
        "description": "Certification project profile",
        "purpose": "",
        "audience": "",
        "tone": "",
        "category": "certification",
        "requirements": [
            {
                "id": "req-001",
                "text": "Describe the business outcome you produced.",
                "required": True,
                "source_lines": [5],
            }
        ],
        "sections": [
            {
                "title": "Business Outcome",
                "description": "",
                "required": True,
                "requirement_ids": ["req-001"],
                "questions": ["Describe the business outcome you produced?"],
            }
        ],
        "constraints": [],
    }

    template = RequirementsIngestionService._normalize(analysis, source, lines)
    questions = [
        question
        for section in template["content"]["sections"]
        for question in section["question_hints"]
    ]

    assert "Describe the business outcome you produced?" in questions
    assert any("Applicant Name" in question and "Applicant Email" in question for question in questions)
    assert not any(
        phrase in question.lower()
        for question in questions
        for phrase in ("table separator", "table cell", "| --- |", "document title")
    )
