# Output Types Plan

## Overview

Add a first-class `output_type` concept that controls how the LLM synthesises interview answers into a final document. Three types are supported: `report`, `blog_post`, and `summary`. Each type uses a distinct synthesis prompt with its own tone, structure, and length expectations.

The output type lives in two places:
- **Template** — sets the default (e.g. a "Book Review" template defaults to `blog_post`)
- **Session** — user can override at session-start time via the existing "Name this session" modal

## Confirmed Design Decisions

- **Sub-task ordering**: model → synthesis → UI picker → display badges → bundled templates
- **Blog post voice**: first-person ("I thought…", "What struck me was…") drawn from the user's own answers
- **Summary format**: 2–4 sentence opener that captures the core finding, followed by bullet points for key details

---

## Sub-Tasks

---

### 1. Backend — Add `output_type` to Template and Session

**Intent**
Store the output type on both the template (default) and the session (user override). Everything flows from these two columns.

**Expected Outcomes**
- `templates` table has a new nullable `output_type` column (defaults to `report`)
- `sessions` table has a new nullable `output_type` column
- Pydantic schemas for both models expose `output_type` on read and write
- `GET /api/templates/` response includes `output_type` per template
- `POST /api/sessions/` accepts `output_type`; falls back to the template's value when omitted
- `PATCH /api/sessions/{id}` and `POST /api/sessions/{id}/autosave` accept `output_type`
- Existing SQLite DB migrated with two `ALTER TABLE` statements

**Todo List**
- [ ] Add `output_type: Mapped[str | None]` to `Template` ORM model (String 50, nullable)
- [ ] Add `output_type: Mapped[str | None]` to `Session` ORM model (String 50, nullable)
- [ ] Add `output_type: str | None` field to `TemplateResponse` schema
- [ ] Add `output_type: str | None` field to `SessionCreate`, `SessionUpdate`, `SessionAutosave`, and `SessionResponse` schemas
- [ ] In `create_session` endpoint: set `session.output_type = session_data.output_type or template.output_type`; requires loading the template at session-create time
- [ ] In `autosave` service method: handle `output_type` alongside name/metadata
- [ ] Run `ALTER TABLE templates ADD COLUMN output_type VARCHAR(50);` and `ALTER TABLE sessions ADD COLUMN output_type VARCHAR(50);` against `data/sessions.db`

**Relevant Context**
- `backend/app/models/template.py` — add column here (mirrors how `name` was added to Session)
- `backend/app/models/session.py` — add column here
- `backend/app/schemas/template.py` — `TemplateResponse`
- `backend/app/schemas/session.py` — `SessionCreate`, `SessionUpdate`, `SessionAutosave`, `SessionResponse`
- `backend/app/api/sessions.py` — `create_session` handler
- `backend/app/services/session_manager.py` — `autosave()`

**Status** — `[x] done`

---

### 2. Backend — Output-Type-Aware Document Synthesis

**Intent**
Give each output type a distinct LLM synthesis prompt so the generated content genuinely differs in structure, tone, and length.

| Type | Persona | Style |
|---|---|---|
| `report` | Precise technical writer | Structured Markdown, section headings, formal prose, complete sentences |
| `blog_post` | Engaging blogger | Narrative flow, first-person voice drawn from answers, opinionated, no rigid section headers |
| `summary` | Executive summariser | Short (≤ 400 words), bullet-point friendly, key facts only |

**Expected Outcomes**
- `LLMProvider.generate_document()` accepts an `output_type: str` argument
- Each value routes to its own system prompt and user-prompt framing
- `_fallback_markdown()` in `DocumentGenerator` is unchanged (it is the structural safety net)
- `DocumentGenerator.generate()` resolves `output_type` from the session record and passes it to the LLM

**Todo List**
- [ ] In `llm_provider.py`: add `output_type: str = "report"` parameter to `generate_document()`
- [ ] Define three prompt variants (system + user) — one per type — inside `generate_document()`
- [ ] In `document_gen.py`: read `session.output_type` (falling back to `"report"`) and pass it to `self.llm.generate_document()`

**Relevant Context**
- `backend/app/services/llm_provider.py` — `generate_document()` at line 195
- `backend/app/services/document_gen.py` — `generate()` at line 53
- The `_complete()` abstraction is shared across all three provider implementations; only the prompt text needs to change, not the plumbing

**Status** — `[x] done`

---

### 3. Frontend — Output Type Picker in Session-Start Modal

**Intent**
Extend the existing `NameSessionModal` to also let the user choose an output type before the session starts. The template's default output type is pre-selected. The choice is passed to `createSession`.

**Expected Outcomes**
- `NameSessionModal` shows three labelled cards / buttons for Report, Blog Post, and Summary with a short description each
- The template's `output_type` (defaulting to `report`) is pre-selected
- Confirmed choice is sent as `output_type` in `api.createSession(templateId, name, outputType)`
- Session object returned from the API has `output_type`; it is passed into `openSession` state so downstream components can read it if needed
- `api.renameSession` (the `PATCH` call) is extended to also accept `output_type` for future re-use

**Todo List**
- [ ] In `api.js`: update `createSession(templateId, name, outputType)` to include `output_type` in the request body
- [ ] In `App.jsx`: pass the template's `output_type` (or `"report"` fallback) as the initial selection into `NameSessionModal`
- [ ] In `NameSessionModal`: add an output-type selector (three clickable cards) below the name input
- [ ] In `startNamed()`: pass the selected output type to `api.createSession`
- [ ] Style the three type cards in `styles.css`

**Relevant Context**
- `frontend/src/App.jsx` — `NameSessionModal` component (~line 71), `startNamed()` (~line 900), `start()` state
- `frontend/src/services/api.js` — `createSession`
- `frontend/src/styles.css` — existing `.modal`, `.modal-actions`, `.name-session-input` patterns to follow

**Status** — `[x] done`

---

### 4. Frontend — Show Output Type on Session Row and in Header

**Intent**
Make the output type visible on the dashboard (recent sessions) and in the active interview header so users always know what kind of document they're producing.

**Expected Outcomes**
- Each session row in the dashboard shows a small badge alongside the status pill (e.g. "Blog Post", "Summary")
- The site header context line (which currently shows the template name) also shows the output type while in an active session
- No new API calls needed — the data is already in the session object

**Todo List**
- [x] In the `Dashboard` session row: render an output-type label next to the status pill
- [x] In the `App` header context: append the output type label when `view !== "dashboard"`
- [x] Add a small `.output-type-badge` CSS class (subtle, muted)

**Relevant Context**
- `frontend/src/App.jsx` — `Dashboard` session row (~line 175), header context (~line 1002)
- `frontend/src/styles.css` — `.status-pill` is the closest visual pattern to follow

**Status** — `[x] done`

---

### 5. Template Files — Add `output_type` to Bundled Templates

**Intent**
Set the `output_type` default on every bundled template JSON file so new sessions inherit the right type automatically.

**Expected Outcomes**
- `templates/project-overview.json` has `"output_type": "report"` in its metadata block
- The `TemplateLoader` reads and stores `output_type` when loading bundled templates
- Any future template JSON can declare `"output_type": "blog_post"` or `"summary"` in its metadata

**Todo List**
- [ ] Add `"output_type": "report"` to `templates/project-overview.json` metadata
- [ ] In `template_loader.py`: read `metadata.output_type` and set it on the `Template` ORM object when loading

**Relevant Context**
- `templates/project-overview.json`
- `backend/app/services/template_loader.py` — `load_bundled_templates()`
- `backend/app/models/template.py`

**Status** — `[x] done`
