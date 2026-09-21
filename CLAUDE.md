# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Interactive Document Creator ("Draftwise") turns a document's requirements into a reusable, guided
Q&A interview and generates a polished document from the answers. Backend is FastAPI + async
SQLAlchemy (SQLite); frontend is a single-page React/Vite app. Voice input uses a local Faster
Whisper model. LLM calls go to OpenAI, Anthropic, or Ollama depending on config.

See `HANDOFF.md` for the fuller running history of what's implemented, known limitations, and
next steps — it's kept up to date at the end of each work session. `docs/IMPLEMENTATION_STATUS.md`
tracks phase definitions/exit gates; `docs/SETUP.md` has setup details.

## Commands

All backend commands run from `backend/` with the venv activated.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements-minimal.txt   # add requirements-pdf.txt for PDF export
cp .env.example .env                                  # then set OPENAI_API_KEY etc.
./run.sh                                               # starts uvicorn with --reload on 127.0.0.1:8000
```

`run.sh` looks for a venv at `backend/.venv`, then `../.venv`, then `backend/venv`, in that order.

```bash
pytest -q                       # run backend tests
pytest tests/test_phase2.py::test_name -q   # run a single test
black app/                      # formatting
ruff check app/                 # linting
mypy app/                       # type checking
```

Frontend, from `frontend/`:

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api to backend on :8000
npm run build
npm run lint
```

API docs are served at `http://localhost:8000/api/docs`; health check at `/health`.

## Architecture

### Backend call graph

`app/main.py` builds the FastAPI app, runs `init_db()` and `load_bundled_templates()` on startup,
and mounts routers under `/api/{sessions,templates,responses,questions,documents,transcriptions,captures}`.
If `frontend/dist` exists, it's served as static files with an SPA fallback (any non-`/api`,
non-`/health` path serves `index.html`) — this is how the built frontend is served in production.

Each API module in `app/api/` is a thin layer over a service in `app/services/`:

- **`requirements_ingestion.py`** — turns pasted/uploaded requirements text into a traceable
  draft template: extracts source, cleans Markdown artifacts, distinguishes headings/tables/form
  fields from actual author-input prompts, and produces numbered source lines used for requirement
  traceability. This is the most complex piece of ingestion logic in the codebase — see the
  `_is_suspicious_question`/`_is_generic_question`/`_requests_author_input` helpers before changing
  question synthesis behavior.
- **`llm_provider.py`** — the `LLMProvider` ABC with `OpenAIProvider`/`AnthropicProvider`/`OllamaProvider`
  implementations, selected via `create_llm_provider()`. All providers implement `_complete()`;
  higher-level methods (`generate_questions`, `review_section`, `generate_document`,
  `analyze_requirements`) are default methods on the ABC that call `_complete()` and parse JSON via
  `_json_from_text()`, which tolerates fenced/truncated model output. `OpenAIProvider` overrides
  `analyze_requirements` to use OpenAI Structured Outputs (`REQUIREMENTS_ANALYSIS_SCHEMA`) instead
  of prompt-based JSON.
- **`question_gen.py`** — loads the approved question list from a saved template (no LLM call) and
  implements the bounded section-review policy: local heuristics
  (`_is_intentional_terminal_answer`, `_is_basic_field_question`, `_is_closed_short_answer`) decide
  whether a completed section is even worth sending to the LLM before calling `review_section()`,
  which returns at most two clarification questions.
- **`document_gen.py`** — `DocumentGenerator.generate()` calls the LLM with an `output_type`
  (`report` | `blog_post` | `summary`, see `session.output_type`) and falls back to deterministic
  Markdown (`_fallback_markdown`) if the LLM call fails. `preview()` returns the deterministic draft
  without calling the LLM, and caches it on `session.generated_document`. `export()` converts
  Markdown to `markdown|html|docx|pdf` (PDF needs the optional `requirements-pdf.txt` deps —
  weasyprint).
- **`session_manager.py`** — autosave/resume/progress tracking and expired-session cleanup.
- **`speech_to_text.py`** — local Faster Whisper transcription (upload and WebSocket streaming).
- **`capture_service.py`** — "Quick Capture" feature: polishes a raw voice transcription into
  `clean_prose` + `structured_breakdown` via an LLM (defaults to Ollama specifically so captured
  ideas stay local unless the user opts into OpenAI — see `capture_llm_provider` in config).
- **`template_loader.py`** — loads bundled JSON templates from `templates/` into the DB on startup,
  skipping any template ID that already exists (so user edits to a bundled template are never
  overwritten).

### The LLM call policy

Calls are deliberately minimized (see `HANDOFF.md` "LLM Call Policy" table for the full mapping).
The important invariants to preserve when touching the interview flow:
- Starting/resuming a session loads the *already-approved* template questions unchanged — no LLM call.
- Section review runs **at most once per section**, reviewing all answers in that section together,
  and returns 0–2 clarification questions that get persisted to session metadata so a resume never
  re-triggers the same review.
- A legacy single-answer follow-up endpoint (`POST /api/questions/followup`) still exists in the
  backend for compatibility but the frontend no longer calls it — don't build new features on it.

### Database

Async SQLAlchemy with SQLite by default (`DATABASE_URL` in `.env`, e.g.
`sqlite+aiosqlite:///../data/sessions.db`, resolved relative to `backend/`). Models live in
`app/models/`: `Template`, `Session` (has many `Response`, cascades on delete), `Response`,
`Capture`. IDs are UUID strings via the custom `UUIDString` `TypeDecorator` in `models/base.py`
(SQLite can't bind native `uuid.UUID` objects — always pass/compare IDs as `str`).

`init_db()` runs `Base.metadata.create_all` *and* a custom `_add_missing_columns()` pass that
diffs each ORM model's declared columns against the actual table and `ALTER TABLE ADD COLUMN`s
anything missing. This means adding a nullable column to a model is enough to migrate existing
SQLite databases on next startup — no Alembic migration is required for that case (Alembic is a
dependency but there's no migrations directory in use).

### Frontend

Single-file React app: `frontend/src/App.jsx` contains the dashboard, requirements-import flow,
template review, question-list review, interview, and preview/export screens as separate
components, driven by `view` state in the top-level `App` component. `frontend/src/services/api.js`
is a thin fetch wrapper (`API_BASE` from `VITE_API_URL`, defaults to relative `/api/...` proxied by
Vite in dev). `frontend/src/components/QuickCapture.jsx` and `frontend/src/hooks/useAudioRecorder.js`
back the standalone Quick Capture flow (`/capture` route, detected via `isCapturePath` in `App.jsx`
and served through the SPA fallback in production).

### Config

`backend/app/config.py` (Pydantic `Settings`, loaded from `backend/.env`) is the single source of
truth for provider selection, model names, storage paths, and Whisper settings. Notable defaults:
`llm_default_provider` is `openai` (Ollama's JSON output for `analyze_requirements` has been found
unreliable — OpenAI is the only verified provider for that call), while `capture_llm_provider`
defaults to `ollama` specifically to keep Quick Capture local by default. All storage paths
(`audio_storage_path`, `session_storage_path`, `template_storage_path`) are relative to `backend/`.

## Testing

`backend/tests/test_phase2.py` holds the integration/regression test suite (pytest-asyncio, mode
`auto` per `pytest.ini`). `backend/tests/fixtures/architect_profile_requirements.md` is a sanitized
realistic ingestion fixture (headings, tables, empty cells, links, fields, choices, narrative
prompts, constraints) used to regression-test the requirements-ingestion pipeline described above —
extend this fixture rather than relying only on synthetic unit inputs when changing ingestion logic.
