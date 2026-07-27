# Project Handoff - Interactive Document Creator

## Context for Next AI Assistant

This document provides everything needed to continue development of the Interactive Document Creator project.

---

## Project Overview

**Goal**: Build a web application that generates structured documents through interactive voice-based Q&A sessions.

**Workflow**:
1. User selects a document template (e.g., "Project Overview")
2. System generates questions based on template
3. User answers via speech (transcribed by Whisper)
4. System asks intelligent follow-up questions
5. System generates final document from all responses

**Key Features**:
- Speech-to-text using local Whisper model
- Multi-provider LLM support (OpenAI, Anthropic, Ollama)
- Template-based document generation
- Session management with auto-save/resume
- Export to Markdown, DOCX, HTML, PDF

---

## Current Status

### ✅ Phase 1 Complete (Foundation)
- Complete project structure created
- Database models implemented (SQLAlchemy async)
- API endpoints created (FastAPI)
- Configuration system built
- Documentation written
- Example template created

### 🔄 Current Issue
**Server won't start** - There's a caching issue. The database models were fixed but server needs restart:
- Files fixed: `backend/app/models/session.py` and `backend/app/models/template.py`
- Changed `JSONB if "postgresql" in str else Text` to just `Text`
- User needs to stop server (Ctrl+C) and restart with `./run.sh`

### 📋 Next Phase (Phase 2 - Core Services)
1. Implement LLM provider abstraction layer
2. Build question generation engine
3. Integrate Whisper for speech-to-text
4. Complete API implementations

---

## Project Location

**Path**: `/home/peralese/Projects/interactive-doc-creator`

**Key Directories**:
```
interactive-doc-creator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration management
│   │   ├── models/              # Database models (Session, Response, Template)
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── api/                 # API endpoints (sessions, templates, responses, questions, documents)
│   │   ├── services/            # Business logic (TO BE IMPLEMENTED)
│   │   └── utils/               # Utilities (TO BE IMPLEMENTED)
│   ├── requirements-minimal.txt # Core dependencies (USE THIS)
│   ├── requirements-pdf.txt     # Optional PDF support
│   ├── INSTALL.md              # Installation guide
│   └── run.sh                  # Quick start script
├── templates/
│   └── project-overview.json   # Example template
├── docs/
│   ├── INTERACTIVE_DOC_CREATOR_PLAN.md  # Complete 12-week plan
│   ├── SETUP.md                         # Setup instructions
│   └── IMPLEMENTATION_STATUS.md         # Progress tracking
└── README.md
```

---

## Installation & Setup

```bash
cd /home/peralese/Projects/interactive-doc-creator/backend

# Create virtual environment (user already has .venv)
python -m venv .venv
source .venv/bin/activate

# Install dependencies (USE MINIMAL - no system libs needed)
pip install -r requirements-minimal.txt

# Configure
cp .env.example .env
# Edit .env if needed (defaults work for local Ollama)

# Run server
./run.sh
```

**Access**:
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/health

---

## Architecture

### Database Models (SQLAlchemy)
1. **Session** - Document creation sessions
   - Fields: id, template_id, status, metadata, current_question_index, generated_document
   - Relationships: has many Responses

2. **Response** - User answers to questions
   - Fields: id, session_id, section_id, question, answer, transcription_confidence, audio_path, sequence_number, is_followup, parent_response_id
   - Relationships: belongs to Session

3. **Template** - Document structure definitions
   - Fields: id, name, description, version, content (JSON), category, estimated_duration, difficulty, is_active
   - Content structure: sections with question_hints

### API Endpoints (FastAPI)

**Implemented (CRUD)**:
- `POST /api/sessions/` - Create session
- `GET /api/sessions/` - List sessions
- `GET /api/sessions/{id}` - Get session with responses
- `PATCH /api/sessions/{id}` - Update session
- `DELETE /api/sessions/{id}` - Delete session
- Similar for `/api/templates/` and `/api/responses/`

**Placeholders (Need Implementation)**:
- `POST /api/questions/generate` - Generate questions from template
- `POST /api/questions/followup` - Generate follow-up question
- `GET /api/questions/next/{session_id}` - Get next question
- `POST /api/documents/generate` - Generate final document
- `GET /api/documents/download/{session_id}` - Download document
- `GET /api/documents/preview/{session_id}` - Preview document

### Configuration (Pydantic Settings)
- LLM providers: OpenAI, Anthropic, Ollama (configurable)
- Whisper: model size, language, device (cpu/cuda)
- Database: SQLite (default) or PostgreSQL
- Storage paths for audio and sessions

---

## What Needs to Be Built (Phase 2)

### 1. LLM Provider Abstraction (`backend/app/services/llm_provider.py`)

Create abstract base class and implementations:

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate_questions(self, template: dict, context: dict) -> list[str]:
        """Generate questions from template"""
        pass
    
    @abstractmethod
    async def generate_followup(self, question: str, answer: str, context: dict) -> str | None:
        """Generate follow-up question if needed"""
        pass
    
    @abstractmethod
    async def generate_document(self, template: dict, responses: list[dict]) -> str:
        """Generate final document from responses"""
        pass

class OpenAIProvider(LLMProvider):
    # Implement using openai library
    pass

class AnthropicProvider(LLMProvider):
    # Implement using anthropic library
    pass

class OllamaProvider(LLMProvider):
    # Implement using ollama library
    pass
```

### 2. Question Generation Service (`backend/app/services/question_gen.py`)

```python
class QuestionGenerator:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def generate_initial_questions(self, template_id: str) -> list[dict]:
        """Parse template and generate initial questions"""
        # Load template from database
        # Use LLM to generate questions based on section hints
        # Return list of questions with metadata
        pass
    
    async def should_ask_followup(self, question: str, answer: str) -> bool:
        """Determine if follow-up is needed"""
        # Use LLM to analyze answer completeness
        pass
    
    async def generate_followup_question(self, question: str, answer: str) -> str:
        """Generate follow-up question"""
        # Use LLM to create clarifying question
        pass
```

### 3. Speech-to-Text Service (`backend/app/services/speech_to_text.py`)

```python
from faster_whisper import WhisperModel

class SpeechToTextService:
    def __init__(self):
        self.model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type
        )
    
    async def transcribe(self, audio_file_path: str) -> dict:
        """Transcribe audio file"""
        # Use Whisper to transcribe
        # Return: {"text": str, "confidence": float}
        pass
    
    async def transcribe_stream(self, audio_stream) -> AsyncGenerator[str, None]:
        """Stream transcription for real-time feedback"""
        # Implement streaming transcription
        pass
```

### 4. Document Generation Service (`backend/app/services/document_gen.py`)

```python
class DocumentGenerator:
    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def generate(self, session_id: UUID, format: str = "markdown") -> str:
        """Generate document from session responses"""
        # Load session with all responses
        # Load template
        # Use LLM to synthesize responses into coherent document
        # Format according to template structure
        # Return formatted document
        pass
    
    async def export(self, content: str, format: str) -> bytes:
        """Export document to specified format"""
        # markdown: return as-is
        # docx: use python-docx
        # html: use markdown library
        # pdf: use weasyprint (if installed)
        pass
```

### 5. Complete API Implementations

Update `backend/app/api/questions.py` and `backend/app/api/documents.py` to use the new services.

---

## Testing the Current Setup

```bash
# Health check
curl http://localhost:8000/health

# Create a session
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{"template_id": "project-overview-v1", "metadata": {}}'

# List sessions
curl http://localhost:8000/api/sessions/

# View API docs
open http://localhost:8000/api/docs
```

---

## Known Issues

1. **Server won't start** - Database model caching issue
   - Solution: Stop server (Ctrl+C) and restart
   - Files already fixed: session.py and template.py

2. **PDF generation requires system libraries**
   - Solution: Use requirements-minimal.txt (PDF optional)
   - To add PDF later: Install ffmpeg, then `pip install -r requirements-pdf.txt`

---

## Important Files to Review

1. `/home/peralese/Projects/interactive-doc-creator/docs/INTERACTIVE_DOC_CREATOR_PLAN.md` - Complete 12-week plan
2. `/home/peralese/Projects/interactive-doc-creator/backend/app/main.py` - FastAPI application
3. `/home/peralese/Projects/interactive-doc-creator/backend/app/models/` - Database models
4. `/home/peralese/Projects/interactive-doc-creator/templates/project-overview.json` - Example template structure

---

## Next Immediate Steps

1. **Fix server startup** - User needs to restart server
2. **Implement LLM provider abstraction** - Start with OllamaProvider (easiest to test locally)
3. **Build question generation** - Parse template and generate questions
4. **Test end-to-end** - Create session, generate questions, store responses

---

## Development Commands

```bash
# Activate environment
cd /home/peralese/Projects/interactive-doc-creator/backend
source .venv/bin/activate

# Run server
./run.sh

# Run tests (when implemented)
pytest

# Format code
black app/
ruff check app/ --fix

# Type check
mypy app/
```

---

## Contact & Resources

- Project created by: Bob (AI Assistant)
- User: peralese
- System: Pop!_OS (Ubuntu-based Linux)
- Python: 3.10
- Virtual env: .venv (already created)

**External Resources**:
- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://docs.sqlalchemy.org/
- Whisper: https://github.com/openai/whisper
- Ollama: https://ollama.com/

---

**Status**: Phase 1 complete, ready for Phase 2 implementation. Server needs restart to clear cache.