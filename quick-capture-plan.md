# Quick Capture — Plan

## Top-Level Overview

Add a **Quick Capture** feature to the existing Interactive Document Creator app. The feature lets a user record a free-flow voice idea at any time, get it transcribed via the existing local Whisper pipeline, then send it to an LLM for polishing into two outputs: clean prose and a structured breakdown. Captures are named and saved to the database for later retrieval.

The feature is accessible two ways:
1. A **"Quick Capture" button** on the Dashboard (within the existing app shell).
2. A **direct `/capture` URL** that loads a focused, minimal UI with no Dashboard chrome — designed as a browser shortcut for capturing ideas on the fly.

A **privacy toggle** at the top of the capture UI lets the user choose per-session whether to polish locally via Ollama (data never leaves the machine) or via OpenAI (cloud, more capable). The toggle defaults to Ollama. The chosen provider is passed as a parameter to the polish API endpoint — no hard-coded backend default.

No new LLM provider code is needed — both `OllamaProvider` and `OpenAIProvider` are already fully implemented.

---

## Sub-Tasks

---

### Sub-Task 1 — Add `Capture` database model and CRUD API

**Intent**
Create the persistence layer for captures: a `Capture` SQLAlchemy model and a `/api/captures/` FastAPI router with create, list, get, and delete endpoints. Captures are stored independently of sessions and templates.

**Expected Outcomes**
- `Capture` table is auto-created on app startup alongside existing tables.
- `POST /api/captures/` saves a new capture (name, raw transcription, clean prose, structured breakdown, audio path, llm\_provider used).
- `GET /api/captures/` returns all captures ordered by created date descending.
- `GET /api/captures/{id}` returns a single capture.
- `DELETE /api/captures/{id}` deletes a capture and its associated audio file if present.
- Pydantic schemas validate all inputs and outputs.

**Todo List**
1. Create `backend/app/models/capture.py` — `Capture` model with fields: `id` (UUID), `name` (str), `raw_transcription` (str), `clean_prose` (str | None), `structured_breakdown` (str | None), `audio_path` (str | None), `llm_provider` (str | None), `created_at`, `updated_at`.
2. Import `Capture` in `backend/app/models/base.py` so `init_db()` picks it up and creates the table on startup.
3. Create `backend/app/schemas/capture.py` — `CaptureCreate`, `CaptureResponse`, `CaptureListResponse` Pydantic schemas.
4. Create `backend/app/api/captures.py` — router with `POST /`, `GET /`, `GET /{id}`, `DELETE /{id}` endpoints. Follow the same async DB session pattern as `backend/app/api/sessions.py`.
5. Register the captures router in `backend/app/main.py` with prefix `/api/captures`.

**Relevant Context**
- [`backend/app/models/base.py`](backend/app/models/base.py) — `Base`, `UUIDString`, `AsyncSessionLocal`, `init_db()` patterns to follow.
- [`backend/app/models/session.py`](backend/app/models/session.py) — model pattern to mirror.
- [`backend/app/schemas/session.py`](backend/app/schemas/session.py) — Pydantic schema pattern.
- [`backend/app/api/sessions.py`](backend/app/api/sessions.py) — router pattern (async DB session dep, HTTPException usage).
- [`backend/app/main.py`](backend/app/main.py) — router registration location.

**Status** — `[ ] pending`

---

### Sub-Task 2 — Add capture polish service and API endpoint

**Intent**
Add the LLM-powered "polish" step: a service method that takes raw transcription text and a chosen provider name, and returns both a clean prose version and a structured breakdown. Expose this as `POST /api/captures/polish`. The provider (`ollama` or `openai`) is passed by the frontend based on the user's privacy toggle — not hard-coded in the backend.

**Expected Outcomes**
- `POST /api/captures/polish` accepts `{ "raw_text": str, "provider": "ollama" | "openai" }` and returns `{ "clean_prose": str, "structured_breakdown": str }`.
- The LLM prompt instructs the model to return a JSON object with `clean_prose` and `structured_breakdown` keys.
- If the LLM call fails, the endpoint returns a 503 with a safe generic error message — no stack trace or exception detail exposed to the client. Full error is logged server-side.
- `ollama` is the default if `provider` is omitted.

**Todo List**
1. Add `capture_llm_provider: Literal["openai", "ollama"] = "ollama"` field to `Settings` in `backend/app/config.py` as the server-side fallback default.
2. Create `backend/app/services/capture_service.py` — `CaptureService` class with an async `polish(raw_text: str, provider: str) -> dict` method. The method calls `create_llm_provider(provider)` and sends a prompt requesting a JSON response with `clean_prose` and `structured_breakdown` keys. Use `_json_from_text()` from `llm_provider.py` to parse the response.
3. Add `POST /polish` route to `backend/app/api/captures.py` (from Sub-Task 1). Accepts `PolishRequest` schema (`raw_text`, optional `provider` defaulting to `"ollama"`), calls `CaptureService().polish()`, returns `PolishResponse`. Catches `LLMProviderError` and returns HTTP 503 with a generic user-facing message; logs full error server-side.
4. Add `PolishRequest` and `PolishResponse` Pydantic schemas to `backend/app/schemas/capture.py`.

**Relevant Context**
- [`backend/app/services/llm_provider.py:119`](backend/app/services/llm_provider.py) — `_json_from_text()` utility to reuse for parsing LLM JSON responses.
- [`backend/app/services/llm_provider.py:382`](backend/app/services/llm_provider.py) — `create_llm_provider()` factory — already supports `"ollama"` and `"openai"`.
- [`backend/app/services/document_gen.py`](backend/app/services/document_gen.py) — pattern for wrapping LLM calls in a service class.
- [`backend/app/config.py:47`](backend/app/config.py) — where to add the `capture_llm_provider` fallback setting.
- Security rule: never expose exception detail to the client — return generic 503 message, log full error server-side only.

**Status** — `[ ] pending`

---

### Sub-Task 3 — Add `/capture` route and URL-based navigation to the frontend

**Intent**
Add URL-based routing to the React frontend so that navigating to `/capture` directly (e.g. as a browser bookmark) loads the Quick Capture view in a focused, chrome-free mode — no Dashboard, no nav. The existing `/` path continues to work unchanged. Uses the browser's `window.location` API — no new npm dependencies.

**Expected Outcomes**
- Navigating to `/capture` loads the app and immediately shows the Quick Capture view with no Dashboard chrome.
- Navigating to `/` shows the Dashboard as before.
- The Vite dev server's SPA fallback serves `index.html` for `/capture` so React handles the route on page load.
- The back-navigation from Quick Capture at `/capture` is a simple "← Back to Dashboard" link that navigates to `/`.

**Todo List**
1. In `frontend/src/App.jsx`, read `window.location.pathname` on initial render to determine the starting view: if the path is `/capture`, set the initial `view` state to `"capture"` and a `standaloneCapture` flag to `true`.
2. Add a `"capture"` case to the view-rendering conditional in `App.jsx` that renders `<QuickCapture>` (built in Sub-Task 4).
3. When `standaloneCapture` is `true`, render only `<QuickCapture>` — suppress all Dashboard chrome (header, nav, sidebar).
4. Check `frontend/vite.config.js` — verify the dev server already has a SPA fallback (serves `index.html` for unknown paths). If not, add it so `/capture` is handled by React on direct load.

**Relevant Context**
- [`frontend/src/App.jsx`](frontend/src/App.jsx) — `view` state and main view-rendering conditional; `setView` navigation pattern.
- [`frontend/vite.config.js`](frontend/vite.config.js) — dev server proxy config; check for existing SPA fallback (`historyApiFallback`).
- No new npm dependencies — use `window.location.pathname` and `window.location.href` only.

**Status** — `[ ] pending`

---

### Sub-Task 4 — Build the QuickCapture React component

**Intent**
Build the `<QuickCapture>` React component — the full UI for recording, transcribing, polishing, naming, and saving a capture. It reuses the existing `useAudioRecorder` hook and `api` service client. Includes a **privacy toggle** so the user explicitly chooses Ollama (local) or OpenAI (cloud) before polishing.

**Expected Outcomes**
- A privacy toggle at the top lets the user choose between "Local (Ollama)" and "Cloud (OpenAI)". Defaults to "Local (Ollama)". The chosen value is passed to `POST /api/captures/polish` as the `provider` field.
- User can record audio using the same record/stop button pattern as the Interview view.
- Raw transcription appears in an editable textarea after recording stops.
- "Polish" button sends the raw text and chosen provider to `POST /api/captures/polish` and shows both outputs (clean prose and structured breakdown).
- User can switch between the two outputs — each shown in its own editable textarea — and selects one to save.
- User enters a name for the capture, then clicks "Save" to call `POST /api/captures/` and persist it.
- A success state confirms the save with the capture name and a "Capture Another" button resets the form.
- A "Saved Captures" section lists previous captures (loaded on mount) with name, date, provider used, and a delete button.
- Error states (mic unavailable, transcription failed, polish failed, save failed) display as inline messages — no raw exception detail shown to the user.

**Todo List**
1. Create `frontend/src/components/QuickCapture.jsx`. Props: `onBack` (callback), `standalone` (bool). Structure the component through phases: `idle` → `recording` → `transcribed` → `polished` → `saved`.
2. Add a privacy toggle UI element at the top — two buttons or a toggle switch labelled "🔒 Local (Ollama)" and "☁️ Cloud (OpenAI)". Store selection in `provider` state, default `"ollama"`.
3. Integrate `useAudioRecorder` hook for mic recording. On stop, call `api.transcribe(blob, null)` — `null` session_id is already accepted by the backend transcription endpoint.
4. Show raw transcription in an editable textarea. Add "Polish" button (disabled while polling).
5. On polish, call `api.polishCapture(rawText, provider)`. Show clean prose and structured breakdown in two tabs or side-by-side cards — each editable. User clicks one to select it as the version to save.
6. Add a name input and "Save Capture" button. Save is disabled until: a name is entered AND (a polish output is selected OR raw text exists).
7. On save, call `api.saveCapture({ name, raw_transcription, clean_prose, structured_breakdown, llm_provider })`. Show success state with "Capture Another" button that resets to `idle`.
8. Load and display saved captures list on mount via `api.listCaptures()`. Refresh after save or delete. Show name, date, provider badge, and delete button per item.
9. Add `api.polishCapture(rawText, provider)`, `api.saveCapture(capture)`, `api.listCaptures()`, `api.deleteCapture(id)` methods to `frontend/src/services/api.js`.
10. Add CSS for the new component to `frontend/src/styles.css` — privacy toggle, phase indicators, output cards, provider badge — following existing BEM-ish naming.

**Relevant Context**
- [`frontend/src/hooks/useAudioRecorder.js`](frontend/src/hooks/useAudioRecorder.js) — hook to reuse directly; identical API to what Interview uses.
- [`frontend/src/services/api.js`](frontend/src/services/api.js) — add new methods following existing fetch patterns.
- [`frontend/src/App.jsx`](frontend/src/App.jsx) — `Interview` component for the recording/transcription UX pattern to mirror.
- [`frontend/src/styles.css`](frontend/src/styles.css) — extend only; do not introduce a new CSS framework.
- Security: display only user-friendly error messages — never surface raw API error bodies to the UI.

**Status** — `[ ] pending`

---

### Sub-Task 5 — Add Quick Capture button to the Dashboard

**Intent**
Add a "Quick Capture" button to the Dashboard so users can access the feature without the direct URL. Clicking it navigates to the capture view within the existing app shell (not standalone mode).

**Expected Outcomes**
- A "Quick Capture" button appears on the Dashboard, visually distinct from existing action buttons.
- Clicking it sets `view` to `"capture"` (non-standalone) via `setView`.
- The Quick Capture view renders with a "← Back to Dashboard" button wired to `setView("dashboard")`.
- No change to any other Dashboard functionality.

**Todo List**
1. In `frontend/src/App.jsx`, locate the Dashboard component's action buttons area and add a "Quick Capture" button. Use the `Mic` icon from `lucide-react` (already installed).
2. Wire the button to `setView("capture")` with `standaloneCapture = false`.
3. In `<QuickCapture>`, when `standalone` prop is `false`, render a "← Back to Dashboard" button at the top wired to `onBack()`.
4. When `standalone` is `true` (loaded via `/capture` URL), render a plain "← Dashboard" link that sets `window.location.href = "/"`.

**Relevant Context**
- [`frontend/src/App.jsx`](frontend/src/App.jsx) — Dashboard component, existing button patterns, `setView`, `lucide-react` imports already in use.
- [`frontend/src/styles.css`](frontend/src/styles.css) — button styling classes to reuse.

**Status** — `[ ] pending`

---

## Out of Scope (Deferred)

- "Start Interview from this Capture" — bridging a capture into a full template session.
- Multi-user isolation / authentication.
- Capture search or tagging.
- Streaming transcription for long recordings.
- Adding Anthropic or other providers to the privacy toggle (can be extended later).
