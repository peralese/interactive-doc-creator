# Product Roadmap and Implementation Status

**Last updated:** 2026-07-27

**Current phase:** Phase 3B — Ingestion Reliability and Source Expansion

**Product goal:** Turn supplied document requirements into a reusable, guided
interview that produces a validated document.

## Product Workflow

The roadmap is organized around the workflow a user must be able to complete:

1. Import the requirements for a document.
2. Convert those requirements into a reusable template.
3. Review and approve the template.
4. Start a document session.
5. Answer initial and clarifying questions by voice or text.
6. Generate a document grounded in those answers.
7. Validate the document against the original requirements.
8. Export, revise, and reuse the template for future documents.

A phase is complete only when its user-facing outcome works end to end. Having
an internal API or data model is not sufficient by itself.

---

## Phase 1 — Platform Foundation ✅ Complete

**Outcome:** The application can persist and expose its core resources.

- [x] FastAPI backend and application configuration
- [x] Async SQLite database
- [x] Template, session, and response models
- [x] CRUD APIs and validation schemas
- [x] React/Vite frontend foundation
- [x] Local development scripts and documentation
- [x] Health checks and API documentation

**Exit gate:** The backend and frontend start locally and can read/write core
application data.

---

## Phase 2 — Guided Authoring Prototype ✅ Complete

**Outcome:** A user can select an existing structured template and complete a
voice- or text-driven document session.

- [x] Bundled Project Overview template
- [x] Template selection
- [x] Session creation, autosave, and resume
- [x] Stable approved-question loading from saved templates
- [x] Full generated-question review before an interview
- [x] Bounded section-level clarification generation
- [x] Persisted clarification questions across session resume
- [x] Browser audio recording
- [x] Local Whisper transcription
- [x] Typed answers and response editing
- [x] Session progress tracking
- [x] Markdown document generation and preview
- [x] Markdown, HTML, and DOCX export
- [x] Optional PDF export
- [x] OpenAI, Anthropic, and Ollama provider adapters
- [x] Offline/template fallbacks

**Exit gate:** The bundled Project Overview workflow can be completed from the
website through document preview and export.

**Known prototype limitations:**

- Imported requirements can generate structured templates, but complex source
  conversion artifacts still require regression testing.
- Clarification review is section-based rather than requirement-coverage-based.
- Generated documents are not yet scored against source requirements.
- WebSocket transcription returns a completed transcript rather than partial
  words while speaking.

---

## Phase 3 — Requirements Ingestion 🚧 Phase 3A Complete; 3B Current

**Outcome:** A non-technical user can supply the rules they received for a new
document type and obtain a draft reusable template.

### 3.1 Source intake

- [x] Add **Import document requirements** to the dashboard
- [x] Support pasted text
- [x] Support TXT and Markdown files
- [ ] Support DOCX files
- [ ] Support text-based PDF files
- [x] Enforce file type and size limits
- [x] Preserve source filename and extraction metadata
- [ ] Clearly report scanned PDFs that require OCR

### 3.2 Requirement extraction

- [x] Extract document purpose, audience, and tone
- [x] Extract required and optional sections
- [x] Extract formatting, length, and submission constraints
- [x] Extract evaluation criteria and mandatory questions
- [x] Preserve traceability from each extracted rule to its source text
- [ ] Represent uncertainty instead of silently inventing requirements

### 3.3 Draft template generation

- [x] Convert extracted requirements into the internal template schema
- [x] Generate interview questions for identified author-input prompts and fields
- [x] Generate a requirement-coverage checklist
- [x] Return a draft without publishing it automatically
- [x] Add ingestion API and service tests

### 3.4 Ingestion reliability

- [x] Remove escaped Markdown formatting before classifying uncovered content
- [x] Ignore empty Markdown cells and table separator rows
- [x] Recognize hash headings and bold-only converted headings
- [x] Separate traceability context from author-input questions
- [x] Prevent formatting artifacts from creating empty interview sections
- [x] Add a regression test for table artifacts, form fields, and real prompts
- [ ] Re-test the corrected pipeline against the complete BadgeMe source
- [ ] Add a sanitized, realistic BadgeMe-style fixture to the repository
- [ ] Detect duplicate, contradictory, and suspiciously generic questions
- [ ] Use strict Structured Outputs/JSON Schema for model analysis

**Phase 3A exit gate:** A user can upload or paste a real requirements document
and receive a traceable draft template without manually writing JSON.

---

## Phase 4 — Template Studio and Reuse 🚧 Partially Implemented

**Outcome:** The user can review, correct, approve, organize, and reuse
generated document types.

- [x] Basic template review wizard
- [x] Edit name, purpose, audience, and tone
- [x] Add, remove, and mark sections required
- [x] Edit interview questions
- [x] Review the complete approved question list before starting
- [x] Return from an active interview to the complete question list
- [ ] Reorder sections and edit coverage rules
- [ ] Review extracted constraints beside their source passages
- [ ] Highlight uncertain or conflicting requirements
- [ ] Validate the template before publication
- [ ] Save drafts and publish approved templates
- [ ] Template versions and change history
- [ ] Duplicate, archive, import, and export templates
- [ ] Template library with categories and search
- [x] Start a session immediately after approval

**Exit gate:** A generated template can be reviewed and published without
developer tools, and then reused for multiple sessions.

---

## Phase 5 — Adaptive Interview and Validated Generation 🚧 Partially Implemented

**Outcome:** The application gathers enough information for every requirement
and proves that the generated document satisfies the supplied rules.

### 5.1 Adaptive interview

- [ ] Track coverage by requirement, not only by question number
- [ ] Evaluate answer completeness before moving on
- [x] Review completed narrative sections for targeted clarifications
- [x] Limit section review to zero, one, or two clarification questions
- [x] Persist generated clarifications and restore them without another LLM call
- [x] Skip LLM review for basic fields, closed short answers, and intentional N/A
- [ ] Drive clarification from explicit requirement-coverage gaps
- [ ] Evaluate and suppress semantically repeated questions across sections
- [ ] Let users skip, defer, or mark information unavailable
- [ ] Show section and overall coverage
- [ ] Preserve unsaved typed answers across refreshes

### 5.2 Grounded document generation

- [x] Generate using the approved template, source rules, and responses
- [ ] Prevent unsupported facts and clearly mark unresolved placeholders
- [ ] Apply required headings, ordering, tone, length, and formatting
- [ ] Regenerate one section without replacing the whole document
- [ ] Preserve user edits when refining other sections

### 5.3 Validation

- [ ] Check every source requirement against the draft
- [ ] Show passed, failed, and unresolved requirements
- [ ] Link validation results to source passages and document sections
- [ ] Block “final” status when mandatory requirements are unresolved
- [ ] Allow justified overrides with an audit note

**Exit gate:** A completed session produces a document with a visible,
traceable coverage report against the original requirements.

---

## Phase 6 — Product Hardening and Deployment 📋 Planned

**Outcome:** The complete workflow is reliable, secure, documented, and easy to
run outside a development environment.

- [ ] Browser end-to-end tests for ingestion through export
- [ ] Unit and integration coverage for extraction and validation
- [ ] Retry, timeout, cancellation, and recovery behavior
- [ ] LLM and Whisper service-status indicators
- [ ] Accessibility and responsive-design audit
- [ ] Structured logging and diagnostics
- [ ] Authentication and multi-user data isolation, if required
- [ ] Data retention and deletion controls
- [ ] Security and dependency review
- [ ] Performance testing for large requirement files
- [ ] Single-command local startup
- [ ] Docker packaging
- [ ] Production configuration and deployment guide
- [ ] User guide and acceptance testing

**Exit gate:** A clean installation can run the documented workflow reliably,
and automated tests cover its critical paths.

---

## Current Capability Snapshot

| Capability | Status |
|---|---|
| Use a bundled JSON template | Working |
| Start, save, and resume a session | Working |
| Answer by voice or text | Working |
| Local speech transcription | Working |
| Generate and export a draft | Working |
| Paste or upload TXT/Markdown requirements | Working |
| Generate templates from requirements | Working |
| Review, edit, and save generated templates | Working |
| Review the complete approved question list | Working; final list is read-only |
| Reuse approved questions without another LLM call | Working |
| Section-level clarification review | Working; maximum two per section |
| Trace extracted requirements to source lines | Working |
| Trace each individual question to requirements | Not implemented |
| DOCX/PDF requirement ingestion | Not implemented |
| Validate output against source requirements | Not implemented |

## Immediate Next Milestone

### Phase 3A ✅ Complete

1. Paste or upload TXT/Markdown requirements.
2. Extract and retain readable text and source metadata.
3. Analyze the text into traceable requirements and a draft template.
4. Review and edit the draft without publishing it automatically.
5. Save the approved template and immediately start its interview.

### Immediate next milestone — Phase 3B

Phase 3B should establish extraction reliability before expanding the number of
supported file formats:

1. Re-import the complete BadgeMe Markdown source and verify the corrected
   question list against the previously valid questions 1–60.
2. Add a sanitized BadgeMe-style fixture covering bold headings, escaped
   formatting, empty table cells, separators, links, checkboxes, form fields,
   and long table rows.
3. Add duplicate-question, suspicious-generic-question, and maximum-question
   validation.
4. Replace free-form model JSON parsing with OpenAI Structured Outputs/JSON
   Schema and explicit content classifications.
5. Represent uncertain or conflicting extracted requirements.
6. Add DOCX extraction.
7. Add text-based PDF extraction.
8. Detect scanned PDFs and clearly report the need for OCR.

---

## Current AI Call Policy

The interview flow intentionally avoids calling the configured LLM after every
answer:

| Event | LLM call |
|---|---|
| Import requirements | Yes — analyze source and draft the reusable template |
| Review or edit template | No |
| Start or resume a session | No — load approved questions unchanged |
| Save an individual answer | No |
| Finish a narrative section | At most once — return zero to two clarifications |
| Finish a basic-field, yes/no, or N/A-only section | No |
| Resume reviewed section | No — restore persisted clarifications |
| Preview document | No — deterministic Markdown preview |
| Refine final document | Yes |

The legacy single-answer follow-up endpoint remains available in the backend,
but the frontend no longer calls it.

## Latest Validation

At commit `7f38553`:

- Backend: 12 tests passed.
- Frontend: ESLint passed.
- Frontend: Vite production build passed.
- One non-blocking Starlette warning remains concerning `httpx` deprecation.
