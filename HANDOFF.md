# Project Handoff — Interactive Document Creator (Draftwise)

**Updated:** September 25, 2026

**Repository:** `https://github.com/peralese/interactive-doc-creator.git`

**Branch:** `main`

**Base commit:** `88d6c6a` — `feat: track in progress / done / published status on dashboard items`

**Working tree:** clean.

## Purpose of This Handoff

This document records the current product behavior, architecture, setup,
completed work, known limitations, and recommended next steps. It is updated
after each significant work session and pushed to the repository so any machine
can pick up where the last session left off.

## Product Goal

Draftwise turns the requirements for a document into a reusable guided
interview:

1. Import a requirements document.
2. Analyze its rules and expected sections.
3. Generate and review an approved question list.
4. Start a document session.
5. Answer by typing or speaking.
6. Ask a small number of useful clarifying questions.
7. Generate and export a document grounded in the supplied answers.
8. Eventually validate the output against every source requirement.

The application is intentionally reusable across different document types; it
is not limited to Project Overview documents.

## Current User Workflow

The following workflow is fully implemented and verified working:

1. Open the dashboard.
2. Choose an existing template or select **Import requirements**.
3. Paste requirements or upload a UTF-8 TXT/Markdown file.
4. The configured LLM (OpenAI by default) analyzes the source into:
   - document identity, purpose, audience, and tone;
   - traceable source requirements;
   - sections and question hints;
   - constraints.
5. Review and edit the generated template.
6. Save the template.
7. Review the complete approved question list before starting.
8. Answer questions by text or local Whisper transcription.
9. At the end of a section, the application may ask for zero to two
   clarifications using all answers from that section.
10. Preview a deterministic Markdown draft.
11. Refine the document with the configured LLM.
12. Reopen the saved draft without regenerating it.
13. Export Markdown, HTML, DOCX, or optional PDF.

## LLM Call Policy

Deliberately designed to control cost, latency, inconsistency, and
follow-up loops.

| Event | LLM call? | Behavior |
|---|---:|---|
| Requirements import | Yes | Analyze source and generate the draft template/questions |
| Review/edit template | No | Local UI state |
| Start or resume session | No | Load approved template questions unchanged |
| Save an individual answer | No | Persist locally |
| Finish a section with narrative content | At most once | Review all section answers and return 0–2 clarifications |
| Basic identity, yes/no, or N/A-only section | No | Closed locally |
| Resume after section review | No | Persisted clarifications are restored from session metadata |
| Preview document | No | Deterministic Markdown preview |
| Refine/generate final document | Yes | Synthesize a polished document |

The legacy single-answer follow-up API still exists in the backend but the
frontend no longer calls it.

## What Has Been Completed

### Phase 1 — Foundation

- FastAPI backend and React/Vite frontend.
- Async SQLAlchemy with SQLite.
- Template, session, and response ORM models (`backend/app/models/`).
- CRUD APIs and Pydantic schemas.
- Configuration through `backend/.env`.
- Health endpoint and OpenAPI documentation.
- Bundled Project Overview template.

### Phase 2 — Guided Authoring

- Template selection and session creation.
- Autosave/resume and response editing.
- Browser microphone recording.
- Local Faster Whisper transcription (`faster-whisper` v1.2.1).
- Typed responses.
- OpenAI, Anthropic, and Ollama provider adapters.
- Deterministic preview plus LLM document refinement.
- Persisted drafts that reopen from Recent sessions without regeneration.
- Recent sessions only list sessions after the first response is saved.
- Markdown, HTML, DOCX, and optional PDF export.

### Phase 3A — Requirements Ingestion

- Paste requirements or upload `.txt`, `.md`, or `.markdown`.
- Source size/type validation.
- LLM-backed requirement analysis (OpenAI default; Ollama supported).
- Source-line traceability.
- Draft template review and editing.
- Save generated templates for reuse.
- Review the complete generated question list before interviewing.
- Return from an interview to the full question list.

### Session 2026-07-27 — Machine Transfer and Startup Fixes

This session migrated the project to a new development machine and resolved
several issues that prevented the application from starting:

- **Added missing `backend/app/models/` package** — the entire ORM models
  directory (`base.py`, `session.py`, `response.py`, `template.py`) was never
  committed to git. The app could not start without it.
- **Fixed `.gitignore`** — a `models/` rule was matching `backend/app/models/`
  (intended to exclude only a top-level Whisper cache). Changed to `/models/`.
- **Fixed `run.sh`** — script checked for `venv/` before `.venv/`; now checks
  `.venv/` first, adds `../.venv/` fallback for project-root venv, fixes error
  message wording, and binds uvicorn to `127.0.0.1` instead of `0.0.0.0`.
- **Fixed default LLM provider** — `config.py` defaulted to `ollama`; changed
  to `openai`. Updated `.env.example` to match (`LLM_DEFAULT_PROVIDER=openai`,
  `OPENAI_MODEL=gpt-5.6-terra`, `OPENAI_TEMPERATURE=1`, `HOST=127.0.0.1`,
  `OLLAMA_MODEL=llama3.1:8b`).
- **Fixed silent LLM fallback** — `POST /api/templates/ingest` was silently
  swallowing `LLMProviderError` and producing a structural draft with no
  warning. Now raises HTTP 503 so the user knows immediately when the provider
  is misconfigured.
- **Fixed UUID binding for SQLite** — ORM models stored IDs as `String(36)`
  but query code passed native `uuid.UUID` objects; SQLite rejected them.
  Added `UUIDString` TypeDecorator that coerces UUID objects to strings on
  bind. Also added explicit `str()` coercion on all `db.get()` PK lookups.
- **Fixed lazy-load error on session resume** — `GET /api/sessions/{id}` and
  `GET /api/sessions/{id}/resume` returned `SessionWithResponses` but responses
  were not eagerly loaded, causing a `MissingGreenlet` error outside an async
  context. Added `selectinload(Session.responses)` to both paths.
- **Diagnosed and fixed Ollama model name** — `.env` had `OLLAMA_MODEL=
  llama3.1:latest` but the installed model tag is `llama3.1:8b`; corrected.

At that checkpoint, **12 backend tests passed**, ESLint passed, and the Vite
build passed.
End-to-end flow verified: requirements imported and parsed successfully using
OpenAI `gpt-5.6-terra`; question list generated correctly.

### Phase 3B Completion

- Verified the full BadgeMe workflow: import, generated questions, voice
  transcription, section-level clarification, draft creation, and AI refinement.
- Added a sanitized architect-profile fixture with headings, tables, empty
  cells, links, fields, choices, narrative prompts, and constraints.
- OpenAI requirement analysis now uses strict Structured Outputs/JSON Schema.
- Extracted requirements include a content classification and confidence.
- Untraceable requirements are rejected rather than silently accepted.
- Duplicate requirements/questions are merged or removed.
- Suspicious formatting questions and redundant generic questions are removed.
- Potentially conflicting constraints and low-confidence extraction are surfaced
  as review warnings.
- Generated questionnaires are capped at 200 questions with a visible warning.

Phase 3B is complete. The current product phase is Phase 4 — Template Studio
and Reuse.

### Aug 4 – Sep 24, 2026 — Features Landed Between Handoff Updates

This file was not updated for these commits; recorded here from the git log so
the history stays continuous:

- `e4ea2d4` / `dd049fd` — session naming and output types
  (`report`, `blog_post`, `summary`).
- `1fac6cc` — Quick Capture: record an idea, transcribe locally, polish into
  clean prose + structured breakdown (Ollama by default, OpenAI opt-in).
- `023b707` — `init_db()` auto-adds missing nullable columns on startup.
- `b74ddca` / `8128793` — backend serves the built frontend; app served over
  the LAN via an HTTPS reverse proxy.
- `1427066` / `dc570f6` — iOS recording reliability; captures merged into the
  dashboard's Recent activity; saved captures can be reopened and edited.

### Session 2026-09-25 — Progress Status (In progress / Done / Published)

Problem: the dashboard had no way to show that work was finished — every
capture showed the same green dot, and a capture already posted to the blog
looked identical to a fresh idea.

Implemented (`88d6c6a`):

- Sessions and captures have `progress_status` (`in_progress` | `done` |
  `published`) and an optional `published_url`. Both are nullable columns, so
  the startup auto-migration adds them; `NULL` reads as `in_progress`.
  Shared validation lives in `backend/app/schemas/progress.py` (URL must be
  `http(s)://`).
- `PATCH /api/sessions/{id}` mirrors progress into the lifecycle `status`:
  done/published → `completed`, back to in progress → `active`. This keeps
  `cleanup_expired()` (which deletes only active/abandoned sessions) from ever
  deleting finished work. `progress_status` is deliberately separate from
  `Session.status`, which the lifecycle/cleanup code owns.
- Status can be changed from a ✓ button on each activity row (modal), the
  document preview sidebar, and the Status step of a saved Quick Capture.
  Choosing Published prompts for the optional link; published rows show a dark
  pill and an external-link icon.
- All activity has status filter chips with counts; the dashboard's Recent
  activity header shows per-status counts that jump to the filtered list.
- The status control reports an error if the server responds without saving
  the requested status, instead of silently reverting.

Operational finding: the long-running backend on `:8000` (started with
`--host 0.0.0.0`, no `--reload`) kept serving old code after the change. It
accepted the PATCH, ignored the unknown fields, and returned 200, so the UI
snapped back to "In progress". **Restart the backend after backend changes**
unless it was started via `./run.sh` (which reloads but binds `127.0.0.1`).
It was restarted with the same flags, logging to `data/backend.log`.

Validation: `pytest -q` — 18 passed (2 new: capture status/URL validation and
session status → lifecycle sync); `npm run lint` and `npm run build` pass; the
auto-migration was verified on a copy of the real `data/sessions.db`; marking a
capture Published was confirmed working in the browser.

## Important Test Case and Findings

The main real-world test document is:

`BadgeMe Architect Project Profile L2 V1.md`

This file is **not in the repository** and must be transferred separately to
each machine. On the current machine it is expected at:

`/home/peralese/Downloads/BadgeMe Architect Project Profile L2 V1.md`

### Markdown Ingestion Fix (commit `7f38553`)

Before this fix, questions 1–60 were mostly good but questions 61+ contained
invalid prompts such as "What content belongs in this table cell?" and "What
table separator should be used here?".

The fix:
- removes escaped Markdown artifacts;
- detects empty cells and separator rows;
- recognizes bold-only headings;
- distinguishes traceability context from author-input prompts;
- only synthesizes questions for actual prompts or form fields;
- avoids creating empty sections for contextual leftovers.

The corrected pipeline has now been re-tested through the complete BadgeMe
workflow. A sanitized equivalent is stored as an automated regression fixture;
old saved templates are not retroactively reanalyzed.

### Ollama vs OpenAI for Requirements Analysis

`llama3.1:8b` is available locally and will respond, but produces poor-quality
structured JSON for the `analyze_requirements` prompt. OpenAI `gpt-5.6-terra`
is the only model verified to produce reliable results for this task.

The default provider is now `openai` in both `config.py` and `.env.example`.
Ollama remains fully supported for all other LLM calls.

## Repository and Transfer Notes

### Tracked in Git

- Backend and frontend source including `backend/app/models/`.
- Tests (`backend/tests/`).
- README, setup documentation, and this handoff.
- `.env.example`.
- Bundled template (`templates/`).
- `package-lock.json`.

### Intentionally Not Tracked

- `backend/.env` — contains API keys; copy manually.
- `.venv/` and `backend/.venv/` — recreate with `pip install`.
- `node_modules/` and frontend build output.
- `data/sessions.db` — contains templates, sessions, and answers.
- `data/audio/` — recorded audio files.
- The BadgeMe Markdown file.
- Whisper model cache (`~/.cache/huggingface/`).

The database path is `data/sessions.db` (relative to the project root, which
resolves correctly when the backend is started from `backend/`).

To continue a session on another machine, securely copy:
1. `data/sessions.db` — preserves all templates, sessions, and answers.
2. `backend/.env` — preserves your API keys and configuration.

Do not commit either file.

## Setup on a New Machine

### 1. Clone

```bash
git clone https://github.com/peralese/interactive-doc-creator.git
cd interactive-doc-creator
git switch main
git pull --ff-only
```

Confirm the expected checkpoint:

```bash
git log -5 --oneline
git status
```

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-minimal.txt
cp .env.example .env
# Edit .env — set OPENAI_API_KEY to the project API key
```

Minimum required `.env` settings:

```env
LLM_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=replace-with-the-project-api-key
OPENAI_MODEL=gpt-5.6-terra
OPENAI_TEMPERATURE=1

WHISPER_MODEL=base
WHISPER_LANGUAGE=en
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

> **Note:** OpenAI API billing is separate from ChatGPT billing. The API
> organization needs a usable credit balance. Project budgets within the
> organization are tracking/alert thresholds only.

Start the backend from `backend/`:

```bash
./run.sh
```

`run.sh` looks for a virtual environment in this order: `backend/.venv`,
`../.venv` (project root), `backend/venv`. Create the venv in whichever
location suits your workflow.

Backend URLs:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/api/docs`
- Health: `http://localhost:8000/health`

### 3. Frontend

In a second terminal:

```bash
cd interactive-doc-creator/frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies `/api` to the backend
on port 8000.

### 4. Microphone / Whisper

Browser speech capture requires:
- an OS audio input device;
- browser microphone permission for localhost;
- `faster-whisper` installed (it is — included in `requirements-minimal.txt`).

The Whisper model weights (~150 MB for `base`) are downloaded from Hugging Face
on first use and cached at `~/.cache/huggingface/`. Subsequent starts are
instant.

If transcription accuracy is poor on technical terms, increase the model in
`.env`:
```env
WHISPER_MODEL=small    # better accuracy, ~2× slower on CPU
WHISPER_MODEL=medium   # best accuracy, notably slower on CPU
```

### 5. Restore session data (optional)

If continuing mid-session from another machine:

```bash
# Copy from the other machine (adjust path as needed)
scp other-machine:~/Development/interactive-doc-creator/data/sessions.db \
    ~/Development/interactive-doc-creator/data/sessions.db
```

## Validation Commands

Backend:

```bash
cd backend
source .venv/bin/activate   # or source ../.venv/bin/activate
pytest -q
```

Expected result:

```text
16 passed, 1 warning
```

The one warning is a non-blocking Starlette deprecation notice about `httpx`.

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Both should pass with no errors.

## Key Implementation Files

- `backend/app/models/base.py`
  — async engine, `UUIDString` type decorator, `init_db`, `get_db`.
- `backend/app/models/session.py`, `response.py`, `template.py`
  — SQLAlchemy ORM models.
- `backend/app/services/requirements_ingestion.py`
  — source extraction, Markdown cleanup, traceability, normalization.
- `backend/app/services/llm_provider.py`
  — OpenAI/Anthropic/Ollama adapters, requirement analysis, section review,
    document synthesis.
- `backend/app/services/question_gen.py`
  — approved question loading, local review gates, section review policy.
- `backend/app/api/questions.py`
  — approved-question endpoint, persisted section review, legacy follow-up.
- `backend/app/api/templates.py`
  — template CRUD and `/ingest` endpoint.
- `backend/app/services/speech_to_text.py`
  — local Faster Whisper transcription.
- `backend/app/services/document_gen.py`
  — preview, refinement, and export.
- `backend/app/models/capture.py`, `backend/app/services/capture_service.py`
  — Quick Capture model and LLM polish.
- `backend/app/schemas/progress.py`
  — shared `progress_status` / `published_url` validation.
- `frontend/src/App.jsx`
  — dashboard, import, template review, question review, interview, preview.
- `frontend/src/components/QuickCapture.jsx`
  — Quick Capture record/polish/save screen.
- `frontend/src/components/ProgressStatus.jsx`, `frontend/src/progressStatus.js`
  — status control, status modal, published link, and shared status helpers.
- `frontend/src/services/api.js`
  — frontend API client.
- `backend/tests/test_phase2.py`
  — current integration and regression tests (18 passing).
- `backend/tests/fixtures/architect_profile_requirements.md`
  — sanitized realistic ingestion regression fixture.

## Current API Highlights

- `POST /api/templates/ingest` — analyze pasted/uploaded requirements.
- `POST /api/templates/` — save an approved template.
- `GET /api/templates/` — list saved templates.
- `POST /api/sessions/` — create a document session.
- `GET /api/sessions/{id}/resume` — resume with stored answers and metadata.
- `POST /api/sessions/{id}/autosave` — persist interview progress.
- `POST /api/questions/generate` — load approved template questions without an LLM call.
- `POST /api/questions/section-review` — run/persist one bounded section review.
- `POST /api/responses/` — save an answer.
- `POST /api/transcriptions/` — transcribe uploaded browser audio.
- `WS /api/transcriptions/stream` — streaming audio transcription.
- `GET /api/documents/preview/{session_id}` — deterministic Markdown preview.
- `POST /api/documents/generate` — LLM refinement.
- `GET /api/documents/download/{session_id}` — export.
- `PATCH /api/sessions/{id}` — rename, or set `progress_status` / `published_url`.
- `GET|POST /api/captures/`, `GET|PATCH|DELETE /api/captures/{id}` — Quick
  Capture CRUD, including `progress_status` / `published_url`.
- `POST /api/captures/polish` — polish a raw transcription (Ollama or OpenAI).

## Known Limitations

1. Only pasted text, TXT, and Markdown requirements are supported; DOCX and
   PDF ingestion are not implemented.
2. Scanned PDF/OCR detection is not implemented.
3. Ollama requirement-analysis quality remains weaker than OpenAI.
4. The post-generation question list is read-only; questions can only be
   edited in the earlier template-review screen.
5. Requirement coverage is stored but interview progress is question-based,
   not requirement-based.
6. Final documents are not validated against source requirements.
7. The legacy per-answer follow-up endpoint remains in the backend.
8. Unsaved text in the current textarea is lost on a browser refresh.
9. No browser end-to-end test suite exists.
10. Authentication, multi-user isolation, deployment packaging, and production
    hardening are not implemented.

## Recommended Next Steps

### Priority 1 — Improve Template/Question Review

- Add safe archive/delete controls and remove the bundled example template.
- Allow editing, deleting, and reordering questions from the question-list
  review screen (currently read-only after generation).
- Add a clear "approved/published" template state.
- Add template version history.
- Show source requirement links beside each question.

### Priority 2 — Requirement-Level Interview Coverage

- Track which answers satisfy which requirements.
- Show section and total coverage during the interview.
- Let users skip, defer, or mark information unavailable.
- Run section review only when coverage indicates a material gap.
- Validate the generated document against required source rules.

### Priority 3 — Additional Source Formats

- Add DOCX extraction first.
- Add text-based PDF extraction.
- Detect scanned/image-only PDFs and report that OCR is required.

## Git Checkpoint

```text
88d6c6a feat: track in progress / done / published status on dashboard items
dc570f6 fix: allow reopening a saved Quick Capture from the dashboard
f7f06af docs: add CLAUDE.md
1427066 fix: iOS recording reliability; merge captures into dashboard
8128793 feat: serve app over LAN via HTTPS reverse proxy
ac9b965 Add missing models package and fix startup and provider issues
3b8994f Align implementation status with current roadmap
711e6b9 Update project handoff for machine transfer
7f38553 Use bounded section-level AI review
a207033 Initial interactive document creator implementation
```

After updating this file:

```bash
git add HANDOFF.md docs/IMPLEMENTATION_STATUS.md
git commit -m "Update handoff for 2026-09-25 session"
git push origin main
```
