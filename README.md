# Interactive Document Creator

A web-based application that guides users through creating structured documents via an interactive question-and-answer workflow with speech-to-text capabilities.

## Features

- 🎤 **Speech-to-Text**: Capture responses via voice using local Whisper model
- 🤖 **AI-Powered Q&A**: Intelligent question generation and follow-ups using LLMs
- 📝 **Template-Based**: Flexible document templates for various use cases
- 💾 **Session Management**: Save progress and resume anytime
- 📄 **Multiple Formats**: Export to Markdown, PDF, DOCX, or HTML
- 🔒 **Privacy-Focused**: Runs entirely locally with no cloud dependencies (optional)
- 🔌 **Flexible LLM Support**: Works with OpenAI, Anthropic, or local Ollama

## Architecture

```
interactive-doc-creator/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── models/   # Database models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── services/ # Business logic
│   │   └── main.py   # FastAPI app
│   ├── requirements-minimal.txt
│   └── run.sh
├── frontend/         # React/Vue frontend
│   └── src/
├── templates/        # Document templates
├── data/            # Storage
│   ├── audio/       # Audio recordings
│   └── sessions/    # Session data
└── docs/            # Documentation
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend)
- (Optional) Ollama for local LLM

### Backend Setup

All backend commands below run from the `backend/` directory. From the project
root:

1. **Enter the backend directory and create the virtual environment**:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with `.venv\Scripts\Activate.ps1`.

2. **Install the core dependencies**:

```bash
python -m pip install -r requirements-minimal.txt
```

3. **Configure environment**:

```bash
cp .env.example .env
# Edit .env with your settings
```

The SQLite database is created automatically on first run.

4. **Run the server**:

```bash
./run.sh
```

Your terminal prompt should be in `interactive-doc-creator/backend` when
running the install and server commands. If you are in the project root, use
`cd backend` first; otherwise `requirements-minimal.txt` and `run.sh` will not
be found.

The API will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/health

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173. Keep the backend
running on port 8000 in a separate terminal; Vite proxies `/api` requests to it.

## Configuration

### LLM Providers

#### OpenAI
```env
LLM_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4
```

#### Anthropic Claude
```env
LLM_DEFAULT_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229
```

#### Ollama (Local)
```env
LLM_DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### Whisper Configuration

```env
WHISPER_MODEL=base  # tiny, base, small, medium, large
WHISPER_LANGUAGE=en
WHISPER_DEVICE=cpu  # or cuda for GPU
```

## Usage

### 1. Import Document Requirements

Open the frontend and choose **Import requirements**. You can paste instructions
or upload a UTF-8 `.txt`, `.md`, or `.markdown` file up to 1 MB.

The application produces an unpublished draft containing:

- Purpose, audience, and tone
- Required sections and interview questions
- Formatting and submission constraints
- A requirement checklist linked to source excerpts

Review and edit the draft, then choose **Save & start interview**.

### 2. Create a Template Manually

Templates define the structure of your document. Example:

```json
{
  "id": "project-overview-v1",
  "name": "Project Overview Document",
  "description": "Comprehensive project overview",
  "version": "1.0",
  "sections": [
    {
      "id": "purpose",
      "title": "Project Purpose",
      "description": "Why this project exists",
      "required": true,
      "question_hints": [
        "What problem does this solve?",
        "Who benefits from this?"
      ]
    }
  ]
}
```

### 3. Start a Session

```bash
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{"template_id": "project-overview-v1"}'
```

### 4. Answer Questions

Use the web interface to:
- Record audio responses
- See real-time transcription
- Answer follow-up questions
- Review and edit responses

### 5. Generate Document

```bash
curl -X POST http://localhost:8000/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id", "format": "markdown"}'
```

## API Endpoints

### Sessions
- `POST /api/sessions/` - Create new session
- `GET /api/sessions/` - List sessions
- `GET /api/sessions/{id}` - Get session details
- `PATCH /api/sessions/{id}` - Update session
- `DELETE /api/sessions/{id}` - Delete session

### Templates
- `POST /api/templates/` - Create template
- `GET /api/templates/` - List templates
- `GET /api/templates/{id}` - Get template
- `PATCH /api/templates/{id}` - Update template
- `DELETE /api/templates/{id}` - Delete template

### Responses
- `POST /api/responses/` - Create response
- `GET /api/responses/session/{session_id}` - List session responses
- `GET /api/responses/{id}` - Get response
- `PATCH /api/responses/{id}` - Update response
- `DELETE /api/responses/{id}` - Delete response

### Questions
- `POST /api/questions/generate` - Generate questions
- `POST /api/questions/followup` - Generate follow-up
- `GET /api/questions/next/{session_id}` - Get next question

### Documents
- `POST /api/documents/generate` - Generate document
- `GET /api/documents/download/{session_id}` - Download document
- `GET /api/documents/preview/{session_id}` - Preview document

### Transcriptions

- `POST /api/transcriptions/` - Upload and transcribe an audio recording
- `WS /api/transcriptions/stream` - Send binary audio frames, then the text
  command `stop`, and receive the completed transcription

### Session Progress

- `POST /api/sessions/{id}/autosave` - Save metadata and interview progress
- `GET /api/sessions/{id}/resume` - Resume with saved responses and progress

## Development

### Run Tests
```bash
cd backend
pytest
```

### Code Formatting
```bash
black app/
ruff check app/
```

### Type Checking
```bash
mypy app/
```

## Project Status

This project is currently in **Phase 3: Requirements Ingestion**.

### Completed
- ✅ Project structure
- ✅ Database models and schemas
- ✅ Configuration management
- ✅ Basic API endpoints
- ✅ LLM provider and document generation services
- ✅ Whisper transcription upload and WebSocket transport
- ✅ Guided React interview interface
- ✅ Browser audio recording, autosave/resume, editing, preview, and downloads
- ✅ Documentation

### Current

- 🚧 Upload or paste document requirements
- 🚧 Extract rules, required sections, and evaluation criteria
- 🚧 Generate a traceable draft template from those requirements

### Planned

- ⏳ Template review, approval, versioning, and reuse
- ⏳ Requirement-aware adaptive interviews
- ⏳ Document validation against the original requirements
- ⏳ End-to-end testing, packaging, and deployment

See [Product Roadmap and Implementation Status](docs/IMPLEMENTATION_STATUS.md)
for phase definitions, exit gates, and the current capability snapshot.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

For questions or issues, please open an issue on GitHub.

## Acknowledgments

- Built with FastAPI, React, and Whisper
- Inspired by conversational document creation workflows
- Designed for privacy and local-first operation
