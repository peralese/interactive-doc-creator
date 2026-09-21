import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  Clock3,
  Download,
  FileText,
  LayoutDashboard,
  LoaderCircle,
  Mic,
  Pencil,
  Plus,
  Save,
  Sparkles,
  Square,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAudioRecorder } from "./hooks/useAudioRecorder";
import { api } from "./services/api";
import { QuickCapture } from "./components/QuickCapture";

const OUTPUT_TYPE_LABELS = { report: "Report", blog_post: "Blog Post", summary: "Summary" };

const formatDate = (value) =>
  new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(value),
  );

const mergeSectionReviews = (approvedQuestions, metadata = {}) => {
  const merged = [...approvedQuestions];
  const reviews = metadata.section_reviews || {};
  Object.entries(reviews).forEach(([sectionId, sectionQuestions]) => {
    const additions = sectionQuestions.filter(
      (candidate) =>
        !merged.some(
          (existing) =>
            existing.is_followup
            && existing.section_id === candidate.section_id
            && existing.question === candidate.question,
        ),
    );
    if (!additions.length) return;
    const lastSectionIndex = merged.reduce(
      (found, question, index) => (question.section_id === sectionId ? index : found),
      -1,
    );
    merged.splice(lastSectionIndex + 1, 0, ...additions);
  });
  return merged;
};

function Spinner({ label = "Working…" }) {
  return (
    <span className="spinner-label">
      <LoaderCircle className="spin" size={17} /> {label}
    </span>
  );
}

function EmptyState({ title, detail }) {
  return (
    <div className="empty-state">
      <FileText size={28} />
      <h3>{title}</h3>
      <p>{detail}</p>
    </div>
  );
}

const OUTPUT_TYPES = [
  { value: "report",    label: "Report",    subtext: "Structured, section-by-section, formal" },
  { value: "blog_post", label: "Blog Post", subtext: "Narrative, first-person, conversational" },
  { value: "summary",   label: "Summary",   subtext: "Short opener + key bullet points" },
];

function NameSessionModal({ template, onConfirm, onCancel, defaultOutputType, nameOnly }) {
  const [name, setName] = useState("");
  const [outputType, setOutputType] = useState(defaultOutputType || "report");
  const placeholder = `e.g. "${template?.name} – ${new Date().toLocaleDateString(undefined, { month: "short", year: "numeric" })}"`;
  return (
    <div className="modal-backdrop">
      <div className="modal">
        <button className="modal-close ghost-icon-button" onClick={onCancel}><X size={18} /></button>
        <h2>Name this session</h2>
        <p style={{ color: "var(--muted)", marginTop: 0, marginBottom: 20, fontSize: 14 }}>
          Give this session a name so you can tell it apart from others using the same template — for example the book title, project name, or date.
        </p>
        <input
          className="name-session-input"
          type="text"
          maxLength={200}
          placeholder={placeholder}
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && name.trim()) onConfirm(name.trim(), outputType); }}
          autoFocus
        />
        {!nameOnly && (
          <div className="output-type-grid">
            {OUTPUT_TYPES.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`output-type-card${outputType === opt.value ? " selected" : ""}`}
                onClick={() => setOutputType(opt.value)}
              >
                <strong>{opt.label}</strong>
                <small>{opt.subtext}</small>
              </button>
            ))}
          </div>
        )}
        <div className="modal-actions">
          <button className="secondary-button" onClick={onCancel}>Cancel</button>
          <button
            className="primary-button"
            disabled={!name.trim()}
            onClick={() => onConfirm(name.trim(), outputType)}
          >
            Start session
          </button>
        </div>
      </div>
    </div>
  );
}

function ActivityRow({ item, templates, onResume, onRename, onOpenCapture, onDeleteCapture }) {
  if (item.type === "session") {
    const session = item.data;
    const template = templates.find((t) => t.id === session.template_id);
    const displayStatus = session.generated_document ? "draft" : session.status;
    const displayName = session.name || template?.name || session.template_id;
    return (
      <div className="session-row-wrap">
        <button className="session-row" onClick={() => onResume(session)}>
          <span className={`status-dot ${displayStatus}`} />
          <span className="session-copy">
            <strong>{displayName}</strong>
            <small>
              {template?.name}{template?.name && session.name ? " · " : ""}Updated {formatDate(session.updated_at)} · Question{" "}
              {session.current_question_index + 1}
            </small>
          </span>
          <span className="output-type-badge">{OUTPUT_TYPE_LABELS[session.output_type] || "Report"}</span>
          <span className="status-pill">{displayStatus}</span>
          <ArrowRight size={18} />
        </button>
        <button
          className="session-rename-btn ghost-icon-button"
          title="Rename session"
          onClick={(e) => { e.stopPropagation(); onRename(session); }}
        >
          <Pencil size={14} />
        </button>
      </div>
    );
  }

  const capture = item.data;
  return (
    <div className="session-row-wrap">
      <button className="session-row" onClick={onOpenCapture}>
        <span className="status-dot completed" />
        <span className="session-copy">
          <strong>{capture.name}</strong>
          <small>
            Quick Capture · {formatDate(capture.created_at)}
            {capture.llm_provider && ` · ${capture.llm_provider === "ollama" ? "Local" : "OpenAI"}`}
          </small>
        </span>
        <span className="output-type-badge">Capture</span>
        <ArrowRight size={18} />
      </button>
      {onDeleteCapture && (
        <button
          className="session-rename-btn ghost-icon-button"
          title="Delete capture"
          onClick={(e) => { e.stopPropagation(); onDeleteCapture(capture); }}
        >
          <Trash2 size={14} />
        </button>
      )}
    </div>
  );
}

function AllActivity({ items, templates, onResume, onRename, onOpenCapture, onDeleteCapture, onBack }) {
  return (
    <main className="dashboard page-shell">
      <section className="section-block recent">
        <div className="section-heading">
          <div>
            <span className="kicker">Everything you’ve created</span>
            <h2>All activity</h2>
          </div>
          <button className="secondary-button" onClick={onBack}>
            <ArrowLeft size={16} /> Dashboard
          </button>
        </div>
        {items.length ? (
          <div className="session-list">
            {items.map((item) => (
              <ActivityRow
                key={`${item.type}-${item.id}`}
                item={item}
                templates={templates}
                onResume={onResume}
                onRename={onRename}
                onOpenCapture={onOpenCapture}
                onDeleteCapture={onDeleteCapture}
              />
            ))}
          </div>
        ) : (
          <EmptyState title="Nothing here yet" detail="Start a document or capture an idea to see it here." />
        )}
      </section>
    </main>
  );
}

function Dashboard({ templates, recentItems, loading, onStart, onResume, onImport, onRename, onCapture, onViewAll }) {
  return (
    <main className="dashboard page-shell">
      <section className="hero">
        <div>
          <span className="eyebrow">Your ideas, thoughtfully structured</span>
          <h1>Turn a conversation into a document worth sharing.</h1>
          <p>
            Choose a format, answer a focused set of questions, and let Draftwise shape your
            thinking into a polished first draft.
          </p>
        </div>
        <div className="hero-mark" aria-hidden="true">
          <span>Dw</span>
        </div>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <span className="kicker">Start something new</span>
            <h2>Choose a document</h2>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="secondary-button import-button" onClick={onCapture}>
              <Mic size={16} /> Quick Capture
            </button>
            <button className="secondary-button import-button" onClick={onImport}>
              <Upload size={16} /> Import requirements
            </button>
          </div>
        </div>
        {loading ? (
          <div className="loading-card"><Spinner label="Loading templates…" /></div>
        ) : templates.length ? (
          <div className="template-grid">
            {templates.map((template, index) => (
              <button
                className="template-card"
                key={template.id}
                onClick={() => onStart(template)}
                style={{ "--delay": `${index * 70}ms` }}
              >
                <span className="template-icon"><FileText size={23} /></span>
                <span className="template-body">
                  <strong>{template.name}</strong>
                  <small>{template.description}</small>
                  <span className="template-meta">
                    {template.estimated_duration ? `${template.estimated_duration} min` : "Guided"}
                    <i />
                    {template.difficulty || "Flexible"}
                  </span>
                </span>
                <ChevronRight size={19} />
              </button>
            ))}
          </div>
        ) : (
          <EmptyState
            title="No templates yet"
            detail="Restart the backend once to load the bundled Project Overview template."
          />
        )}
      </section>

      <section className="section-block recent">
        <div className="section-heading">
          <div>
            <span className="kicker">Pick up where you left off</span>
            <h2>Recent activity</h2>
          </div>
          {recentItems.length > 5 && (
            <button className="text-button" onClick={onViewAll}>
              View all <ChevronRight size={15} />
            </button>
          )}
        </div>
        {recentItems.length ? (
          <div className="session-list">
            {recentItems.slice(0, 5).map((item) => (
              <ActivityRow
                key={`${item.type}-${item.id}`}
                item={item}
                templates={templates}
                onResume={onResume}
                onRename={onRename}
                onOpenCapture={onCapture}
              />
            ))}
          </div>
        ) : (
          <p className="quiet">Your saved sessions and captures will appear here.</p>
        )}
      </section>
    </main>
  );
}

function RequirementsImport({ onCancel, onAnalyze }) {
  const [mode, setMode] = useState("paste");
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState("");
  const ready = mode === "paste" ? text.trim().length >= 20 : Boolean(file);

  const submit = async () => {
    setAnalyzing(true);
    setError("");
    try {
      await onAnalyze({ text: mode === "paste" ? text : "", file: mode === "file" ? file : null });
    } catch (caught) {
      setError(caught.message);
      setAnalyzing(false);
    }
  };

  return (
    <main className="import-page page-shell">
      <button className="text-button" onClick={onCancel}><ArrowLeft size={16} /> Dashboard</button>
      <div className="import-heading">
        <span className="eyebrow">Create a reusable document type</span>
        <h1>Import document requirements</h1>
        <p>
          Add the instructions, rubric, or required sections you received. Draftwise will turn
          them into a template you can inspect before saving.
        </p>
      </div>
      <section className="import-card">
        <div className="source-tabs" role="tablist">
          <button className={mode === "paste" ? "active" : ""} onClick={() => setMode("paste")}>
            Paste instructions
          </button>
          <button className={mode === "file" ? "active" : ""} onClick={() => setMode("file")}>
            Upload TXT or Markdown
          </button>
        </div>
        {mode === "paste" ? (
          <div className="source-field">
            <label htmlFor="requirements">Document requirements</label>
            <textarea
              id="requirements"
              value={text}
              onChange={(event) => setText(event.target.value)}
              placeholder={"Example:\n# Project Summary\nMust explain the business problem and intended users.\n\n# Success Measures\nInclude measurable outcomes and a target date."}
              autoFocus
            />
            <span>{text.length.toLocaleString()} characters · minimum 20</span>
          </div>
        ) : (
          <label className={`file-drop ${file ? "selected" : ""}`}>
            <Upload size={26} />
            <strong>{file ? file.name : "Choose a requirements file"}</strong>
            <span>{file ? `${Math.ceil(file.size / 1024)} KB selected` : "TXT, MD, or Markdown · up to 1 MB"}</span>
            <input
              type="file"
              accept=".txt,.md,.markdown,text/plain,text/markdown"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
            />
          </label>
        )}
        <div className="privacy-note">
          <LayoutDashboard size={16} />
          <span>The source stays in your local workspace and is attached to the saved template for traceability.</span>
        </div>
        {error && <div className="error-banner">{error}</div>}
        <div className="import-actions">
          <button className="secondary-button" onClick={onCancel}>Cancel</button>
          <button className="primary-button" disabled={!ready || analyzing} onClick={submit}>
            {analyzing ? <Spinner label="Analyzing requirements…" /> : <><Sparkles size={17} /> Analyze requirements</>}
          </button>
        </div>
      </section>
    </main>
  );
}

function TemplateReview({ draft, analysisMode, warnings, onBack, onSave }) {
  const [template, setTemplate] = useState(draft);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const requirements = template.content.requirements || [];

  const updateSection = (sectionIndex, patch) => {
    setTemplate((current) => ({
      ...current,
      content: {
        ...current.content,
        sections: current.content.sections.map((section, index) =>
          index === sectionIndex ? { ...section, ...patch } : section,
        ),
      },
    }));
  };
  const removeSection = (sectionIndex) => {
    setTemplate((current) => ({
      ...current,
      content: {
        ...current.content,
        sections: current.content.sections.filter((_, index) => index !== sectionIndex),
      },
    }));
  };
  const addSection = () => {
    const number = template.content.sections.length + 1;
    setTemplate((current) => ({
      ...current,
      content: {
        ...current.content,
        sections: [
          ...current.content.sections,
          {
            id: `new-section-${number}`,
            title: "New Section",
            description: "",
            required: true,
            requirement_ids: [],
            question_hints: ["What information should this section include?"],
          },
        ],
      },
    }));
  };
  const updateQuestion = (sectionIndex, questionIndex, value) => {
    const section = template.content.sections[sectionIndex];
    updateSection(sectionIndex, {
      question_hints: section.question_hints.map((question, index) =>
        index === questionIndex ? value : question,
      ),
    });
  };

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await onSave(template);
    } catch (caught) {
      setError(caught.message);
      setSaving(false);
    }
  };

  return (
    <main className="review-page page-shell">
      <div className="review-top">
        <button className="text-button" onClick={onBack}><ArrowLeft size={16} /> Requirements</button>
        <div>
          <span className="eyebrow">Review before saving</span>
          <h1>Draft document template</h1>
          <p>Correct the interpretation now. The saved template will drive every future interview.</p>
        </div>
        <div className="analysis-badge">
          <Sparkles size={15} />
          {analysisMode === "llm" ? "AI analyzed" : "Basic structural draft"}
        </div>
      </div>
      {warnings.map((warning) => <div className="warning-banner" key={warning}>{warning}</div>)}
      <div className="review-layout">
        <section className="review-editor">
          <div className="review-card identity-card">
            <span className="kicker">Document identity</span>
            <label>
              Name
              <input
                value={template.name}
                onChange={(event) => setTemplate({ ...template, name: event.target.value })}
              />
            </label>
            <label>
              Description
              <textarea
                value={template.description || ""}
                onChange={(event) => setTemplate({ ...template, description: event.target.value })}
              />
            </label>
            <div className="three-fields">
              {["purpose", "audience", "tone"].map((field) => (
                <label key={field}>
                  {field}
                  <input
                    value={template.content[field] || ""}
                    placeholder={`Not identified`}
                    onChange={(event) =>
                      setTemplate({
                        ...template,
                        content: { ...template.content, [field]: event.target.value },
                      })
                    }
                  />
                </label>
              ))}
            </div>
          </div>
          <div className="review-section-heading">
            <div><span className="kicker">Interview structure</span><h2>Sections and questions</h2></div>
            <button className="secondary-button" onClick={addSection}><Plus size={15} /> Add section</button>
          </div>
          {template.content.sections.map((section, sectionIndex) => (
            <div className="review-card section-editor" key={`${section.id}-${sectionIndex}`}>
              <div className="section-editor-top">
                <span className="section-number">{String(sectionIndex + 1).padStart(2, "0")}</span>
                <input
                  className="section-title-input"
                  value={section.title}
                  onChange={(event) => updateSection(sectionIndex, { title: event.target.value })}
                />
                <label className="required-toggle">
                  <input
                    type="checkbox"
                    checked={section.required}
                    onChange={(event) => updateSection(sectionIndex, { required: event.target.checked })}
                  />
                  Required
                </label>
                <button className="bare-icon" onClick={() => removeSection(sectionIndex)} title="Remove section">
                  <Trash2 size={16} />
                </button>
              </div>
              <input
                className="description-input"
                value={section.description}
                placeholder="Describe what belongs in this section"
                onChange={(event) => updateSection(sectionIndex, { description: event.target.value })}
              />
              <div className="question-list">
                <span>Questions</span>
                {section.question_hints.map((question, questionIndex) => (
                  <div key={questionIndex}>
                    <span>{questionIndex + 1}</span>
                    <input
                      value={question}
                      onChange={(event) => updateQuestion(sectionIndex, questionIndex, event.target.value)}
                    />
                    <button
                      className="bare-icon"
                      title="Remove question"
                      onClick={() =>
                        updateSection(sectionIndex, {
                          question_hints: section.question_hints.filter((_, index) => index !== questionIndex),
                        })
                      }
                    >
                      <X size={15} />
                    </button>
                  </div>
                ))}
                <button
                  className="add-question"
                  onClick={() =>
                    updateSection(sectionIndex, {
                      question_hints: [...section.question_hints, "What else should be covered?"],
                    })
                  }
                >
                  <Plus size={14} /> Add question
                </button>
              </div>
              <div className="trace-row">
                {section.requirement_ids.length} linked source requirement
                {section.requirement_ids.length === 1 ? "" : "s"}
              </div>
            </div>
          ))}
        </section>
        <aside className="source-review">
          <div className="source-review-sticky">
            <span className="kicker">Source traceability</span>
            <h2>{requirements.length} requirements found</h2>
            <p>{template.content.source.filename}</p>
            <div className="requirement-list">
              {requirements.map((requirement) => (
                <article key={requirement.id}>
                  <div><code>{requirement.id}</code>{requirement.required && <span>required</span>}</div>
                  <strong>{requirement.text}</strong>
                  {requirement.source_excerpt && <blockquote>{requirement.source_excerpt}</blockquote>}
                </article>
              ))}
            </div>
          </div>
        </aside>
      </div>
      {error && <div className="error-banner review-error">{error}</div>}
      <div className="review-savebar">
        <span>{template.content.sections.length} sections · {template.content.sections.reduce((sum, section) => sum + section.question_hints.length, 0)} questions</span>
        <button
          className="primary-button"
          disabled={!template.name.trim() || !template.content.sections.length || saving}
          onClick={save}
        >
          {saving ? <Spinner label="Saving template…" /> : <><Save size={17} /> Save & start interview</>}
        </button>
      </div>
    </main>
  );
}

function AnswerEditor({ response, onSave, onClose }) {
  const [value, setValue] = useState(response.answer);
  const [saving, setSaving] = useState(false);
  return (
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className="modal" onMouseDown={(event) => event.stopPropagation()}>
        <button className="icon-button modal-close" onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>
        <span className="kicker">Edit response</span>
        <h2>{response.question}</h2>
        <textarea value={value} onChange={(event) => setValue(event.target.value)} autoFocus />
        <button
          className="primary-button"
          disabled={!value.trim() || saving}
          onClick={async () => {
            setSaving(true);
            await onSave(response.id, value.trim());
            setSaving(false);
          }}
        >
          {saving ? <Spinner label="Saving…" /> : <><Save size={17} /> Save response</>}
        </button>
      </div>
    </div>
  );
}

function QuestionReview({ template, questions, responses, onContinue, onExit }) {
  const sections = template.content?.sections || [];
  const sectionDetails = new Map(
    sections.map((section) => [section.id, section]),
  );
  const groupedQuestions = questions.reduce((groups, question, index) => {
    const sectionId = question.section_id || "general";
    if (!groups.has(sectionId)) groups.set(sectionId, []);
    groups.get(sectionId).push({ ...question, reviewNumber: index + 1 });
    return groups;
  }, new Map());
  const answeredCount = responses.length;

  return (
    <main className="question-review-page page-shell">
      <div className="question-review-heading">
        <button className="text-button" onClick={onExit}>
          <ArrowLeft size={16} /> Dashboard
        </button>
        <div>
          <span className="eyebrow">Review before answering</span>
          <h1>Interview question list</h1>
          <p>
            These are the questions generated from <strong>{template.name}</strong>. Review the
            complete interview structure before you begin, or return here at any time.
          </p>
        </div>
        <div className="question-count-badge">
          <strong>{questions.length}</strong>
          <span>questions</span>
        </div>
      </div>

      <div className="generated-question-sections">
        {[...groupedQuestions.entries()].map(([sectionId, sectionQuestions], sectionIndex) => {
          const section = sectionDetails.get(sectionId);
          return (
            <section className="generated-question-section" key={sectionId}>
              <div className="generated-section-heading">
                <span>{String(sectionIndex + 1).padStart(2, "0")}</span>
                <div>
                  <h2>{section?.title || sectionId.replaceAll(/[-_]/g, " ")}</h2>
                  {section?.description && <p>{section.description}</p>}
                </div>
                <small>{sectionQuestions.length} question{sectionQuestions.length === 1 ? "" : "s"}</small>
              </div>
              <ol className="generated-question-list">
                {sectionQuestions.map((question) => (
                  <li key={`${question.sequence_number}-${question.reviewNumber}-${question.question}`}>
                    <span>{question.reviewNumber}</span>
                    <p>{question.question}</p>
                    {question.is_followup && <small>Follow-up</small>}
                  </li>
                ))}
              </ol>
            </section>
          );
        })}
      </div>

      <div className="question-review-actions">
        <span>
          {answeredCount
            ? `${answeredCount} response${answeredCount === 1 ? "" : "s"} already saved`
            : "No responses saved yet"}
        </span>
        <button className="primary-button" onClick={onContinue}>
          {answeredCount ? "Return to interview" : "Start interview"} <ArrowRight size={17} />
        </button>
      </div>
    </main>
  );
}

function Interview({
  template,
  session,
  questions,
  responses,
  onSaveAnswer,
  onEditResponse,
  onReviewQuestions,
  onPreview,
  onExit,
}) {
  const answeredInitial = new Set(
    responses.filter((item) => !item.is_followup).map((item) => item.sequence_number),
  );
  const answeredFollowups = new Set(
    responses
      .filter((item) => item.is_followup)
      .map((item) => `${item.sequence_number}:${item.question}`),
  );
  const firstUnanswered = questions.findIndex((question) =>
    question.is_followup
      ? !answeredFollowups.has(`${question.sequence_number}:${question.question}`)
      : !answeredInitial.has(question.sequence_number),
  );
  const [index, setIndex] = useState(firstUnanswered < 0 ? questions.length : firstUnanswered);
  const [answer, setAnswer] = useState("");
  const [saving, setSaving] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(null);
  const [pendingBlob, setPendingBlob] = useState(null);
  const current = questions[index];
  const progress = questions.length ? Math.min(100, (responses.length / questions.length) * 100) : 0;

  const handleRecording = useCallback(
    async (blob) => {
      setTranscribing(true);
      setError("");
      try {
        const result = await api.transcribe(blob, session.id);
        setAnswer((value) => `${value}${value ? " " : ""}${result.text}`.trim());
        setPendingBlob(null);
      } catch (caught) {
        // Keep the recorded audio so a failed upload (e.g. a dropped
        // connection during a long transcription) doesn't force re-recording.
        setPendingBlob(blob);
        setError(caught.message);
      } finally {
        setTranscribing(false);
      }
    },
    [session.id],
  );
  const recorder = useAudioRecorder(handleRecording);

  const submit = async () => {
    if (!answer.trim() || !current) return;
    setSaving(true);
    setError("");
    try {
      await onSaveAnswer(current, answer.trim());
      setAnswer("");
      setIndex((value) => value + 1);
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  };

  if (!current) {
    return (
      <main className="complete-screen page-shell">
        <div className="complete-card">
          <span className="completion-icon"><Check size={30} /></span>
          <span className="eyebrow">Interview complete</span>
          <h1>You’ve given us plenty to work with.</h1>
          <p>Review your responses or generate a polished draft now. You can return and edit later.</p>
          <div className="button-row">
            <button className="secondary-button" onClick={() => setIndex(Math.max(0, questions.length - 1))}>
              <ArrowLeft size={17} /> Back
            </button>
            <button className="primary-button" onClick={onPreview}>
              <Sparkles size={17} /> Create my draft
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <>
      <main className="interview-layout page-shell">
        <aside className="interview-aside">
          <button className="text-button" onClick={onExit}><ArrowLeft size={16} /> Dashboard</button>
          <div className="aside-title">
            <span className="template-icon"><FileText size={20} /></span>
            <div><small>Creating</small><strong>{template.name}</strong></div>
          </div>
          <button className="secondary-button review-questions-button" onClick={onReviewQuestions}>
            <FileText size={15} /> Review all questions
          </button>
          <div className="progress-copy">
            <span>{Math.min(responses.length, questions.length)} of {questions.length} answered</span>
            <strong>{Math.round(progress)}%</strong>
          </div>
          <div className="progress-track"><span style={{ width: `${progress}%` }} /></div>
          <div className="response-history">
            <span className="kicker">Your responses</span>
            {responses.map((response) => (
              <button key={response.id} onClick={() => setEditing(response)}>
                <Check size={14} />
                <span><strong>{response.question}</strong><small>{response.answer}</small></span>
                <Pencil size={13} />
              </button>
            ))}
            {!responses.length && <p className="quiet">Answers are saved as you go.</p>}
          </div>
        </aside>

        <section className="question-stage">
          <div className="question-topline">
            <span>Question {index + 1}</span>
            <span>{current.section_id.replaceAll("_", " ")}</span>
          </div>
          <h1>{current.question}</h1>
          <p className="question-help">Speak naturally or type your response. A thoughtful paragraph is plenty.</p>
          <div className={`answer-box ${recorder.recording ? "recording" : ""}`}>
            <textarea
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder="Start typing your answer…"
              disabled={transcribing}
              autoFocus
            />
            <div className="answer-tools">
              <span>{answer.length ? `${answer.split(/\s+/).filter(Boolean).length} words` : "Not saved yet"}</span>
              {transcribing ? (
                <Spinner label="Transcribing…" />
              ) : recorder.recording ? (
                <button className="record-button active" onClick={recorder.stop}>
                  <Square size={14} fill="currentColor" /> Stop · {recorder.seconds}s
                </button>
              ) : (
                <button className="record-button" onClick={() => recorder.start().catch((caught) => setError(caught.message))}>
                  <Mic size={16} /> Answer with voice
                </button>
              )}
            </div>
          </div>
          {error && (
            <div className="error-banner">
              {error}
              {pendingBlob && (
                <button
                  className="text-button"
                  onClick={() => handleRecording(pendingBlob)}
                  disabled={transcribing}
                >
                  Retry transcription
                </button>
              )}
            </div>
          )}
          <div className="question-actions">
            <button
              className="secondary-button"
              disabled={index === 0}
              onClick={() => setIndex((value) => Math.max(0, value - 1))}
            >
              <ArrowLeft size={17} /> Previous
            </button>
            <button className="primary-button" disabled={!answer.trim() || saving} onClick={submit}>
              {saving ? <Spinner label="Saving…" /> : <>Save & continue <ArrowRight size={17} /></>}
            </button>
          </div>
        </section>
      </main>
      {editing && (
        <AnswerEditor
          response={editing}
          onClose={() => setEditing(null)}
          onSave={async (id, value) => {
            await onEditResponse(id, value);
            setEditing(null);
          }}
        />
      )}
    </>
  );
}

function Preview({ session, content, loading, onGenerate, onBack }) {
  const [format, setFormat] = useState("markdown");
  return (
    <main className="preview-layout page-shell">
      <aside className="preview-panel">
        <button className="text-button" onClick={onBack}><ArrowLeft size={16} /> Back to interview</button>
        <span className="eyebrow">Your draft</span>
        <h1>Ready for a closer look.</h1>
        <p>Generate a refined version, then download it in the format that suits your workflow.</p>
        <button className="primary-button wide" onClick={onGenerate} disabled={loading}>
          {loading ? <Spinner label="Generating…" /> : <><Sparkles size={17} /> Refine with AI</>}
        </button>
        <div className="download-control">
          <label htmlFor="format">Download format</label>
          <div>
            <select id="format" value={format} onChange={(event) => setFormat(event.target.value)}>
              <option value="markdown">Markdown</option>
              <option value="html">HTML</option>
              <option value="docx">Word (.docx)</option>
              <option value="pdf">PDF (optional)</option>
            </select>
            <a className="icon-button" href={api.downloadUrl(session.id, format)} title="Download">
              <Download size={18} />
            </a>
          </div>
        </div>
      </aside>
      <article className="paper">
        {loading && !content ? (
          <div className="paper-loading"><Spinner label="Composing your draft…" /></div>
        ) : (
          <MarkdownDocument content={content} />
        )}
      </article>
    </main>
  );
}

function MarkdownDocument({ content }) {
  if (!content) return <EmptyState title="Nothing to preview yet" detail="Answer at least one question first." />;
  return (
    <>
      {content.split("\n").map((line, index) => {
        if (line.startsWith("# ")) return <h1 key={index}>{line.slice(2)}</h1>;
        if (line.startsWith("## ")) return <h2 key={index}>{line.slice(3)}</h2>;
        if (line.startsWith("**") && line.endsWith("**"))
          return <h3 key={index}>{line.slice(2, -2)}</h3>;
        return line ? <p key={index}>{line}</p> : <br key={index} />;
      })}
    </>
  );
}

const isCapturePath = window.location.pathname === "/capture";

export default function App() {
  const [view, setView] = useState(isCapturePath ? "capture" : "dashboard");
  const [standaloneCapture] = useState(isCapturePath);
  const [templates, setTemplates] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [captures, setCaptures] = useState([]);
  const [template, setTemplate] = useState(null);
  const [session, setSession] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [responses, setResponses] = useState([]);
  const [document, setDocument] = useState("");
  const [ingestion, setIngestion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [namingTemplate, setNamingTemplate] = useState(null); // template pending a name before session create
  const [renamingSession, setRenamingSession] = useState(null); // session pending a rename

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setMessage("");
    try {
      const [templateData, sessionData, captureData] = await Promise.all([
        api.templates(),
        api.sessions(100),
        api.listCaptures(100),
      ]);
      setTemplates(templateData.templates);
      setSessions(sessionData.sessions);
      setCaptures(captureData.captures);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  // Sessions and Quick Captures are separate entities but share one "recent
  // activity" timeline on the dashboard, sorted by most recent activity.
  const recentItems = useMemo(() => {
    const sessionItems = sessions.map((item) => ({
      type: "session",
      id: item.id,
      timestamp: item.updated_at,
      data: item,
    }));
    const captureItems = captures.map((item) => ({
      type: "capture",
      id: item.id,
      timestamp: item.updated_at || item.created_at,
      data: item,
    }));
    return [...sessionItems, ...captureItems].sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp),
    );
  }, [sessions, captures]);

  const openSession = async (
    selectedTemplate,
    activeSession,
    destination = "interview",
    savedDocument = "",
  ) => {
    setLoading(true);
    setMessage("");
    try {
      const questionData = await api.questions(activeSession.id, selectedTemplate.id);
      setTemplate(selectedTemplate);
      setSession(activeSession);
      setQuestions(mergeSectionReviews(questionData, activeSession.metadata));
      setResponses(activeSession.responses || []);
      setDocument(savedDocument);
      setView(destination);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const start = (selectedTemplate) => {
    // Show the naming modal; actual session creation happens after the user confirms.
    setNamingTemplate(selectedTemplate);
  };

  const startNamed = async (selectedTemplate, name, outputType) => {
    setNamingTemplate(null);
    setLoading(true);
    try {
      const created = await api.createSession(selectedTemplate.id, name, outputType);
      await openSession(
        selectedTemplate,
        { ...created, responses: [] },
        "review-questions",
      );
    } catch (error) {
      setMessage(error.message);
      setLoading(false);
    }
  };

  const resume = async (savedSession) => {
    const selectedTemplate = templates.find((item) => item.id === savedSession.template_id);
    if (!selectedTemplate) return setMessage("This session’s template is unavailable.");
    setLoading(true);
    try {
      const resumed = await api.resumeSession(savedSession.id);
      await openSession(
        selectedTemplate,
        resumed,
        resumed.generated_document ? "preview" : "interview",
        resumed.generated_document || "",
      );
    } catch (error) {
      setMessage(error.message);
      setLoading(false);
    }
  };

  const saveAnswer = async (question, answer) => {
    const saved = await api.saveResponse({
      session_id: session.id,
      section_id: question.section_id,
      question: question.question,
      answer,
      sequence_number: question.sequence_number,
      is_followup: question.is_followup,
      parent_response_id: question.parent_response_id || null,
    });
    setResponses((items) => [...items, saved]);
    if (question.is_followup) return;
    const position = questions.indexOf(question);
    const sectionIsComplete = !questions
      .slice(position + 1)
      .some((item) => !item.is_followup && item.section_id === question.section_id);
    if (!sectionIsComplete) return;
    try {
      const clarifications = await api.reviewSection(session.id, question.section_id);
      if (clarifications.length) {
        setQuestions((items) => {
          const next = [...items];
          const insertionPoint = next.indexOf(question) + 1;
          const existing = new Set(
            next
              .filter((item) => item.is_followup)
              .map((item) => `${item.section_id}:${item.question}`),
          );
          const additions = clarifications.filter(
            (item) => !existing.has(`${item.section_id}:${item.question}`),
          );
          next.splice(insertionPoint, 0, ...additions);
          return next;
        });
      }
    } catch {
      // The primary response is safely stored; follow-ups are optional enrichment.
    }
  };

  const preview = async () => {
    setView("preview");
    setLoading(true);
    try {
      const result = await api.preview(session.id);
      setDocument(result.content);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  };

  const analyzeRequirements = async (source) => {
    const result = await api.ingestRequirements(source);
    setIngestion(result);
    setView("review-template");
  };

  const saveImportedTemplate = async (draft) => {
    const saved = await api.createTemplate(draft);
    setTemplates((items) => [...items.filter((item) => item.id !== saved.id), saved]);
    setIngestion(null);
    start(saved); // Will open the naming modal
  };

  const renameSession = async (targetSession, name) => {
    setRenamingSession(null);
    try {
      const updated = await api.renameSession(targetSession.id, name);
      setSessions((items) => items.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setMessage(error.message);
    }
  };

  const deleteCapture = async (capture) => {
    try {
      await api.deleteCapture(capture.id);
      setCaptures((items) => items.filter((item) => item.id !== capture.id));
    } catch (error) {
      setMessage(error.message);
    }
  };

  const templateName = useMemo(() => template?.name || "Draftwise", [template]);

  return (
    <div className="app">
      <header className="site-header">
        <button className="brand" onClick={() => { setView("dashboard"); loadDashboard(); }}>
          <span>Dw</span>
          <strong>Draftwise</strong>
        </button>
        <div className="header-context">
          {view !== "dashboard" && <><span>{templateName}{session?.output_type ? ` · ${OUTPUT_TYPE_LABELS[session.output_type]}` : ""}</span><i /></>}
          <span className="local-badge">Local workspace</span>
        </div>
      </header>

      {message && <div className="global-error"><span>{message}</span><button onClick={() => setMessage("")}><X size={16} /></button></div>}
      {namingTemplate && (
        <NameSessionModal
          template={namingTemplate}
          defaultOutputType={namingTemplate?.output_type || "report"}
          onConfirm={(name, outputType) => startNamed(namingTemplate, name, outputType)}
          onCancel={() => setNamingTemplate(null)}
        />
      )}
      {renamingSession && (
        <NameSessionModal
          template={templates.find((t) => t.id === renamingSession.template_id)}
          nameOnly
          onConfirm={(name) => renameSession(renamingSession, name)}
          onCancel={() => setRenamingSession(null)}
        />
      )}
      {view === "dashboard" && (
        <Dashboard
          templates={templates}
          recentItems={recentItems}
          loading={loading}
          onStart={start}
          onResume={resume}
          onImport={() => setView("import-requirements")}
          onRename={(s) => setRenamingSession(s)}
          onCapture={() => setView("capture")}
          onViewAll={() => setView("all-activity")}
        />
      )}
      {view === "all-activity" && (
        <AllActivity
          items={recentItems}
          templates={templates}
          onResume={resume}
          onRename={(s) => setRenamingSession(s)}
          onOpenCapture={() => setView("capture")}
          onDeleteCapture={deleteCapture}
          onBack={() => setView("dashboard")}
        />
      )}
      {view === "capture" && (
        <QuickCapture
          standalone={standaloneCapture}
          onBack={() => { setView("dashboard"); loadDashboard(); }}
        />
      )}
      {view === "import-requirements" && (
        <RequirementsImport
          onCancel={() => setView("dashboard")}
          onAnalyze={analyzeRequirements}
        />
      )}
      {view === "review-template" && ingestion && (
        <TemplateReview
          draft={ingestion.template}
          analysisMode={ingestion.analysis_mode}
          warnings={ingestion.warnings}
          onBack={() => setView("import-requirements")}
          onSave={saveImportedTemplate}
        />
      )}
      {view === "review-questions" && template && session && (
        <QuestionReview
          template={template}
          questions={questions}
          responses={responses}
          onContinue={() => setView("interview")}
          onExit={() => { setView("dashboard"); loadDashboard(); }}
        />
      )}
      {view === "interview" && (
        <Interview
          key={session.id}
          template={template}
          session={session}
          questions={questions}
          responses={responses}
          onSaveAnswer={saveAnswer}
          onReviewQuestions={() => setView("review-questions")}
          onEditResponse={async (id, answer) => {
            const updated = await api.updateResponse(id, answer);
            setResponses((items) => items.map((item) => (item.id === id ? updated : item)));
          }}
          onPreview={preview}
          onExit={() => { setView("dashboard"); loadDashboard(); }}
        />
      )}
      {view === "preview" && (
        <Preview
          session={session}
          content={document}
          loading={loading}
          onBack={() => setView("interview")}
          onGenerate={async () => {
            setLoading(true);
            try {
              const result = await api.generate(session.id);
              setDocument(result.content);
            } catch (error) {
              setMessage(error.message);
            } finally {
              setLoading(false);
            }
          }}
        />
      )}
      {!standaloneCapture && (
        <footer>
          <span><LayoutDashboard size={14} /> Private by default</span>
          <span><Clock3 size={14} /> Progress saves automatically</span>
        </footer>
      )}
    </div>
  );
}
