# Project Handoff — Interactive Document Creator

**Updated:** July 27, 2026

**Repository:** `https://github.com/peralese/interactive-doc-creator.git`

**Branch:** `main`

**Current commit:** `7f38553` — `Use bounded section-level AI review`

## Purpose of This Handoff

This project is moving to another development machine. This document records
the current product behavior, architecture, setup, completed work, known
limitations, and recommended next steps.

The repository is clean and synchronized with `origin/main` at the commit above
before this handoff update. `HANDOFF.md` itself will need to be committed and
pushed after this edit if the new machine will retrieve it from GitHub.

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

The following workflow is implemented:

1. Open the dashboard.
2. Choose an existing template or select **Import requirements**.
3. Paste requirements or upload a UTF-8 TXT/Markdown file.
4. OpenAI (or the configured provider) analyzes the source into:
   - document identity, purpose, audience, and tone;
   - traceable source requirements;
   - sections and question hints;
   - constraints.
5. Review and edit the generated template.
6. Save the template.
7. Review the complete approved question list before starting.
8. Answer questions by text or local Whisper transcription.
9. At the end of a section, the application may ask OpenAI for zero to two
   clarifications using all answers from that section.
10. Preview a deterministic Markdown draft.
11. Refine the document with the configured LLM.
12. Export Markdown, HTML, DOCX, or optional PDF.

## LLM Call Policy

This was deliberately changed to control cost, latency, inconsistency, and
follow-up loops.

| Event | OpenAI call? | Behavior |
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

The legacy single-answer follow-up API still exists, but the frontend no longer
calls it.

## What Has Been Completed

### Phase 1 — Foundation

- FastAPI backend and React/Vite frontend.
- Async SQLAlchemy with SQLite.
- Template, session, and response models.
- CRUD APIs and Pydantic schemas.
- Configuration through `backend/.env`.
- Health endpoint and OpenAPI documentation.
- Bundled Project Overview template.

### Phase 2 — Guided Authoring

- Template selection and session creation.
- Autosave/resume and response editing.
- Browser microphone recording.
- Local Faster Whisper transcription.
- Typed responses.
- OpenAI, Anthropic, and Ollama provider adapters.
- Deterministic preview plus LLM document refinement.
- Markdown, HTML, DOCX, and optional PDF export.

### Phase 3A — Requirements Ingestion

- Paste requirements or upload `.txt`, `.md`, or `.markdown`.
- Source size/type validation.
- OpenAI-backed requirement analysis.
- Source-line traceability.
- Draft template review and editing.
- Save generated templates for reuse.
- Review the complete generated question list before interviewing.
- Return from an interview to the full question list.

### Recent Corrections

- Updated README setup to use `.venv`.
- Switched the tested requirements analyzer from local Llama to OpenAI
  `gpt-5.6-terra`.
- Correct OpenAI temperature for this model is `1`; `0.2` is rejected.
- Added a question-review screen before the interview.
- Prevented follow-up questions from recursively generating follow-ups.
- Accepted intentional answers such as `N/A`, `none`, `unknown`, and
  “I do not have a mentor.”
- Suppressed follow-ups for names, emails, dates, roles, locations, and other
  basic fields.
- Reworked Markdown ingestion so table separators, empty cells, formatting
  artifacts, and bold headings do not become interview questions.
- Changed the LLM call policy from per-answer review to bounded section-level
  review.
- Persisted section clarifications in session metadata so they survive resume.

## Important Test Case and Findings

The main real-world test document was:

`/home/peralese/Downloads/BadgeMe Architect Project Profile L2 V1.md`

This file is outside the repository and must be transferred separately if it
will be used on the new machine.

Before the Markdown fix, questions 1–60 were mostly good, but questions 61+
contained invalid prompts such as:

- “What content belongs in this table cell?”
- “What table separator should be used here?”
- “What is the section title?”

Cause: the source-coverage augmentation treated uncovered Markdown formatting
as requirements, then the question generator rephrased those artifacts.

Implemented fix:

- remove escaped Markdown artifacts;
- detect empty cells and separator rows;
- recognize bold-only headings;
- distinguish traceability context from author-input prompts;
- only synthesize questions for actual prompts or form fields;
- avoid creating empty sections for contextual leftovers.

A new import/template is required to test this fix. Existing saved templates
retain their old generated question lists.

## Repository and Transfer Notes

### Tracked in Git

- Backend and frontend source.
- Tests.
- README, setup documentation, and this handoff.
- `.env.example`.
- Bundled template.
- `package-lock.json`.

### Intentionally Not Tracked

- `backend/.env` and API keys.
- `.venv/` and `backend/.venv/`.
- `node_modules/` and frontend build output.
- SQLite databases (`*.db`).
- Recorded audio.
- The BadgeMe Markdown file in `Downloads`.

The current configured database path is:

`data/sessions.db`

There is also an older `backend/data/sessions.db` on the original machine. The
default configuration used when running from `backend/` points to
`../data/sessions.db`.

If existing templates, sessions, and answers must be preserved, securely copy
`data/sessions.db` to the same relative location on the new machine. Otherwise,
the application will create a fresh database. Do not commit the database.

## Setup on the New Machine

### 1. Clone

```bash
git clone https://github.com/peralese/interactive-doc-creator.git
cd interactive-doc-creator
git switch main
git pull --ff-only
```

Confirm the expected checkpoint:

```bash
git log -3 --oneline
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
```

Configure `backend/.env` without committing the key:

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

OpenAI API billing is separate from ChatGPT billing. The API organization needs
a usable credit balance. Projects within the same OpenAI organization draw from
the organization balance; project budgets are primarily tracking/alert
thresholds.

Start the backend from `backend/` so relative `.env`, database, audio, and
template paths resolve correctly:

```bash
./run.sh
```

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

The frontend normally runs at `http://localhost:5173` and proxies `/api` to the
backend on port 8000.

### 4. Microphone

Browser speech capture requires:

- an operating-system input device;
- browser microphone permission for localhost;
- the backend and local Whisper dependencies.

On the original Pop!_OS machine, “Requested device not found” was caused by a
blank system input device. Once an input device was available, transcription
worked.

## Validation Commands

Backend:

```bash
cd backend
source .venv/bin/activate
pytest -q
```

Last verified result:

```text
12 passed
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
```

Last verified results:

- ESLint passed.
- Vite production build passed.

There is one non-blocking Starlette test warning about `httpx` deprecation.

## Key Implementation Files

- `backend/app/services/requirements_ingestion.py`
  - source extraction, Markdown cleanup, traceability, normalization.
- `backend/app/services/llm_provider.py`
  - OpenAI/Anthropic/Ollama adapters, requirement analysis, section review,
    document synthesis.
- `backend/app/services/question_gen.py`
  - approved question loading, local review gates, section review policy.
- `backend/app/api/questions.py`
  - approved-question endpoint, persisted section review, legacy follow-up.
- `backend/app/services/speech_to_text.py`
  - local Faster Whisper transcription.
- `backend/app/services/document_gen.py`
  - preview, refinement, and export.
- `frontend/src/App.jsx`
  - dashboard, import, template review, question review, interview, preview.
- `frontend/src/services/api.js`
  - frontend API client.
- `backend/tests/test_phase2.py`
  - current integration and regression tests.

## Current API Highlights

- `POST /api/templates/ingest` — analyze pasted/uploaded requirements.
- `POST /api/templates/` — save an approved template.
- `POST /api/sessions/` — create a document session.
- `GET /api/sessions/{id}/resume` — resume with stored answers and metadata.
- `POST /api/questions/generate` — load approved template questions without an
  LLM call.
- `POST /api/questions/section-review` — run/persist one bounded section review.
- `POST /api/responses/` — save an answer.
- `POST /api/transcriptions/` — transcribe uploaded browser audio.
- `GET /api/documents/preview/{session_id}` — deterministic preview.
- `POST /api/documents/generate` — LLM refinement.
- `GET /api/documents/download/{session_id}` — export.

## Known Limitations

1. Only pasted text, TXT, and Markdown requirements are supported.
2. DOCX and PDF ingestion are not implemented.
3. Scanned PDF/OCR detection is not implemented.
4. Requirement analysis still uses prompt-generated JSON rather than OpenAI
   Structured Outputs/JSON Schema.
5. The Markdown cleanup is heuristic and needs more realistic fixtures.
6. Questions can be reviewed before an interview, but the post-generation
   review list is currently read-only. Template questions can be edited in the
   earlier template-review screen.
7. Requirement coverage is stored, but interview progress is still primarily
   question-based rather than requirement-based.
8. Final documents are not validated against every source requirement.
9. The legacy per-answer follow-up endpoint remains in the backend.
10. Unsaved text in the current textarea is not preserved across a refresh.
11. No browser end-to-end test suite exists.
12. Authentication, multi-user isolation, deployment packaging, and production
    hardening are not implemented.

## Recommended Next Steps

### Priority 1 — Re-test the Real Markdown Import

1. Copy the BadgeMe Markdown file to the new machine.
2. Start the backend with OpenAI configured.
3. Import it as a new requirements document.
4. Confirm formatting artifacts no longer appear as questions.
5. Compare the new list against the previously valid questions 1–60.
6. Record any missing, duplicated, or misclassified prompts as fixtures.

Do not evaluate the fix using the old saved template; re-import the source.

### Priority 2 — Add a Realistic Ingestion Fixture Suite

- Add a sanitized version of the complex Markdown structure under tests.
- Test bold headings, escaped formatting, empty cells, separator rows, links,
  checkbox questions, form fields, and long `<br>` table rows.
- Assert important prompts are retained.
- Assert formatting artifacts never become questions.
- Add duplicate-question and maximum-question-count checks.

### Priority 3 — Use OpenAI Structured Outputs

- Replace free-form JSON extraction/repair with a strict JSON Schema.
- Add explicit content types:
  - heading;
  - instruction/context;
  - form field;
  - choice/checkbox;
  - narrative prompt;
  - constraint;
  - reference/link.
- Validate every model response before publishing a draft.
- Represent uncertainty and conflicts explicitly.

### Priority 4 — Improve Template/Question Review

- Allow editing, deleting, and reordering questions from the full question-list
  review screen.
- Add a clear “approved/published” template state.
- Add template version history.
- Show source requirement links beside each question.

### Priority 5 — Requirement-Level Interview Coverage

- Track which answers satisfy which requirements.
- Show section and total coverage.
- Let users skip, defer, or mark information unavailable.
- Run section review only when coverage indicates a material gap.
- Validate the generated document against required source rules.

### Priority 6 — Additional Source Formats

- Add DOCX extraction first.
- Add text-based PDF extraction.
- Detect scanned/image-only PDFs and report that OCR is required.

## Suggested First Session on the New Machine

1. Clone and configure the project.
2. Run all tests and frontend validation.
3. Copy the real BadgeMe Markdown file and optionally `data/sessions.db`.
4. Re-import the BadgeMe file.
5. Review the new generated question list.
6. Fix any remaining ingestion classifications and add them as regression
   tests.
7. Commit and push that verified checkpoint before beginning DOCX/PDF work.

## Git Checkpoint

Existing commits:

```text
7f38553 Use bounded section-level AI review
a207033 Initial interactive document creator implementation
```

After updating this file:

```bash
git add HANDOFF.md
git commit -m "Update project handoff for machine transfer"
git push origin main
```
